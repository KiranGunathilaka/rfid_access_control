import os, io, csv, json, time, threading
from typing import Optional, Literal, List, Tuple
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Serial is optional at import time so the API can still run without it.
try:
    import serial  # pyserial
except Exception:
    serial = None

# -------------------------------------------------------
# Config & DB
# -------------------------------------------------------
load_dotenv()

DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:password@127.0.0.1:3306/rfid_access_control")
API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"

SERIAL_PORT = os.getenv("SERIAL_PORT", "")     # e.g., "COM10" or "/dev/ttyUSB0"
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))

def _env_int(name: str, default: Optional[int]) -> Optional[int]:
    v = os.getenv(name)
    return int(v) if v and v.isdigit() else default

GATE_ID  = _env_int("GATE_ID", None)
BOOTH_ID = _env_int("BOOTH_ID", None)
DEVICE_ID= _env_int("DEVICE_ID", None)
NODE_ID  = _env_int("NODE_ID", None)

engine: Engine = create_engine(
    DB_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    isolation_level="READ COMMITTED",
    future=True,
)

app = FastAPI(title="RFID Access Control API", version="1.1")

# -------------------------------------------------------
# Types & Models
# -------------------------------------------------------
UserType = Literal["Common", "VIP", "Backstage"]
GateType = Literal["Common_IN", "Common_Out", "VIP", "Backstage"]
UserStatus = Literal["IDLE", "In", "Out", "Expired", "Banned"]
EventType = Literal["ENTRY", "EXIT", "DENIED"]
ResultType = Literal["PASS", "FAIL"]

class ScanIn(BaseModel):
    rfid_tag: str = Field(..., min_length=1, max_length=100)
    gate_id: int
    booth_id: int
    device_id: int
    node_id: int

class ScanOut(BaseModel):
    result: ResultType
    message: str
    event_type: EventType

class CreateUserIn(BaseModel):
    rfid_tag: str
    name: Optional[str] = None
    nic: Optional[str] = None
    user_type: UserType = "Common"

class CreateUserOut(BaseModel):
    id: Optional[int]
    success: bool
    message: str

class SyncStatusRow(BaseModel):
    node_id: int
    table_name: str
    last_sync_timestamp: datetime
    sync_status: Literal["SUCCESS","FAILED","IN_PROGRESS"]
    error_message: Optional[str] = None
    minutes_since_sync: int

# -------------------------------------------------------
# Core business helpers (shared by HTTP & Serial worker)
# -------------------------------------------------------
def _determine_event(current_status: UserStatus) -> Tuple[EventType, UserStatus]:
    if current_status in ("IDLE", "Out"):
        return "ENTRY", "In"
    elif current_status == "In":
        return "EXIT", "Out"
    return "DENIED", current_status

def _enforce_direction(gate_type: GateType, event: EventType) -> bool:
    if gate_type == "Common_IN"  and event == "EXIT":
        return False
    if gate_type == "Common_Out" and event == "ENTRY":
        return False
    return True

def _enforce_gate_audience(gate_type: GateType, user_type: UserType) -> bool:
    if gate_type == "VIP":
        return user_type == "VIP"
    if gate_type == "Backstage":
        return user_type == "Backstage"
    return True

def _log_denied(conn, user_id: Optional[int], user_type: UserType, gate_id:int, booth_id:int, node_id:int, msg:str):
    conn.execute(
        text("""
            INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
            VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)
        """),
        {"uid": user_id, "ut": user_type, "gate": gate_id, "booth": booth_id, "msg": msg, "node": node_id}
    )

def process_scan_tx(conn, rfid_tag:str, gate_id:int, booth_id:int, device_id:int, node_id:int) -> Tuple[ResultType, str, EventType, Optional[int], Optional[str]]:
    """
    Runs inside a DB transaction (conn is `engine.begin()` connection).
    Returns: (result, message, event_type, user_id, user_name)
    """
    # Validate topology
    booth = conn.execute(text("SELECT gate_id, device_id FROM booths WHERE id=:bid"), {"bid": booth_id}).mappings().first()
    if not booth or booth["gate_id"] != gate_id:
        _log_denied(conn, None, "Common", gate_id, booth_id, node_id, "Topology error: booth does not belong to gate")
        return "FAIL", "Topology error: booth does not belong to gate", "DENIED", None, None
    if booth["device_id"] != device_id:
        _log_denied(conn, None, "Common", gate_id, booth_id, node_id, "Topology error: device not assigned to booth")
        return "FAIL", "Topology error: device not assigned to booth", "DENIED", None, None

    dev = conn.execute(text("SELECT gate_id FROM devices WHERE id=:did"), {"did": device_id}).mappings().first()
    if not dev or dev["gate_id"] != gate_id:
        _log_denied(conn, None, "Common", gate_id, booth_id, node_id, "Topology error: device not wired to gate")
        return "FAIL", "Topology error: device not wired to gate", "DENIED", None, None

    node = conn.execute(text("SELECT gate_id FROM nodes WHERE id=:nid"), {"nid": node_id}).mappings().first()
    if not node or node["gate_id"] != gate_id:
        _log_denied(conn, None, "Common", gate_id, booth_id, node_id, "Topology error: node not mounted at gate")
        return "FAIL", "Topology error: node not mounted at gate", "DENIED", None, None

    gate = conn.execute(text("SELECT type FROM gates WHERE id=:gid"), {"gid": gate_id}).mappings().first()
    if not gate:
        _log_denied(conn, None, "Common", gate_id, booth_id, node_id, "Invalid gate")
        return "FAIL", "Invalid gate", "DENIED", None, None
    gate_type: GateType = gate["type"]

    # Find user (lock row to avoid race)
    user = conn.execute(
        text("SELECT id, name, user_type, status FROM users WHERE rfid_tag=:tag FOR UPDATE"),
        {"tag": rfid_tag}
    ).mappings().first()

    if not user:
        msg = "Unknown RFID tag"
        conn.execute(
            text("""INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (NULL, 'Common', 'DENIED', :gate, :booth, 'FAIL', :msg, :node)"""),
            {"gate": gate_id, "booth": booth_id, "msg": msg, "node": node_id}
        )
        return "FAIL", msg, "DENIED", None, None

    user_id = user["id"]
    user_name = user["name"] or None
    user_type: UserType = user["user_type"]
    status: UserStatus = user["status"]

    if status in ("Banned","Expired"):
        msg = f"Access denied - {status}"
        conn.execute(
            text("""INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)"""),
            {"uid": user_id, "ut": user_type, "gate": gate_id, "booth": booth_id, "msg": msg, "node": node_id}
        )
        return "FAIL", msg, "DENIED", user_id, user_name

    event, new_status = _determine_event(status)
    if not _enforce_direction(gate_type, event):
        msg = "Wrong direction for this gate"
        conn.execute(
            text("""INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)"""),
            {"uid": user_id, "ut": user_type, "gate": gate_id, "booth": booth_id, "msg": msg, "node": node_id}
        )
        return "FAIL", msg, "DENIED", user_id, user_name

    if not _enforce_gate_audience(gate_type, user_type):
        msg = f"Access denied - gate restricted to {gate_type}"
        conn.execute(
            text("""INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)"""),
            {"uid": user_id, "ut": user_type, "gate": gate_id, "booth": booth_id, "msg": msg, "node": node_id}
        )
        return "FAIL", msg, "DENIED", user_id, user_name

    # Update user + insert log
    conn.execute(
        text("""UPDATE users
                SET status=:new_status,
                    last_seen_at=CURRENT_TIMESTAMP,
                    last_gate_id=:gate,
                    last_booth_id=:booth,
                    last_result='PASS',
                    node_id=:node
                WHERE id=:uid"""),
        {"new_status": new_status, "gate": gate_id, "booth": booth_id, "node": node_id, "uid": user_id}
    )

    msg = f"Access granted - {event}"
    conn.execute(
        text("""INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                VALUES (:uid, :ut, :evt, :gate, :booth, 'PASS', :msg, :node)"""),
        {"uid": user_id, "ut": user_type, "evt": event, "gate": gate_id, "booth": booth_id, "msg": msg, "node": node_id}
    )
    return "PASS", msg, event, user_id, user_name

# -------------------------------------------------------
# HTTP endpoints
# -------------------------------------------------------
@app.post("/api/scan", response_model=ScanOut)
def handle_scan(payload: ScanIn):
    with engine.begin() as conn:
        result, message, event, _, _ = process_scan_tx(
            conn, payload.rfid_tag, payload.gate_id, payload.booth_id, payload.device_id, payload.node_id
        )
        if result == "FAIL":
            # turn DB-side message into HTTP 400 for clients that expect failure codes
            raise HTTPException(status_code=400, detail=message)
        return ScanOut(result=result, message=message, event_type=event)

@app.post("/api/users", response_model=CreateUserOut)
def create_user(body: CreateUserIn):
    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("""INSERT INTO users (rfid_tag, name, nic, user_type, status)
                        VALUES (:tag, :name, :nic, :ut, 'IDLE')"""),
                {"tag": body.rfid_tag, "name": body.name, "nic": body.nic, "ut": body.user_type}
            )
            new_id = res.lastrowid
            return CreateUserOut(id=new_id, success=True, message="User added")
    except Exception as e:
        if API_DEBUG: print("create_user error:", e)
        return CreateUserOut(id=None, success=False, message="RFID tag already exists or DB error")

@app.post("/api/users/import")
def import_users(file: UploadFile = File(...)):
    inserted = 0
    duplicates = 0
    data = file.file.read()
    try:
        text_stream = io.StringIO(data.decode("utf-8"))
        reader = csv.DictReader(text_stream)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV encoding")

    with engine.begin() as conn:
        for row in reader:
            try:
                conn.execute(
                    text("""INSERT INTO users (rfid_tag, name, nic, user_type, status)
                            VALUES (:tag, :name, :nic, :ut, 'IDLE')"""),
                    {"tag": (row.get("rfid_tag") or "").strip(),
                     "name": (row.get("name") or None),
                     "nic": (row.get("nic") or None),
                     "ut":  (row.get("user_type") or "Common").strip() or "Common"}
                )
                inserted += 1
            except Exception:
                duplicates += 1
                continue
    return {"inserted": inserted, "duplicates": duplicates}

@app.get("/api/sync/status", response_model=List[SyncStatusRow])
def sync_status():
    with engine.begin() as conn:
        rows = conn.execute(
            text("""SELECT node_id, table_name, last_sync_timestamp, sync_status, error_message,
                           TIMESTAMPDIFF(MINUTE, last_sync_timestamp, NOW()) AS minutes_since_sync
                    FROM sync_status_view
                    ORDER BY node_id, table_name""")
        ).mappings().all()
        return [SyncStatusRow(**row) for row in rows]

# -------------------------------------------------------
# Serial worker (runs in background on startup)
# -------------------------------------------------------
EVENT_CODE = {"DENIED": 0, "ENTRY": 1, "EXIT": 2}

def _serial_loop():
    if serial is None:
        if API_DEBUG: print("[serial] pyserial not installed; skipping UART worker.")
        return
    # Sanity checks
    if not SERIAL_PORT or None in (GATE_ID, BOOTH_ID, DEVICE_ID, NODE_ID):
        if API_DEBUG:
            print("[serial] Missing SERIAL_PORT or gate/booth/device/node IDs. Set them in .env to enable UART.")
        return

    while True:
        try:
            if API_DEBUG: print(f"[serial] Opening {SERIAL_PORT} @ {SERIAL_BAUD} …")
            ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
            if API_DEBUG: print("[serial] Port open.")
            while True:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception as e:
                    if API_DEBUG: print("[serial] Bad line:", line, e)
                    continue

                if msg.get("t") != "req":
                    continue

                req_id = msg.get("id")
                mac    = msg.get("mac")
                uid    = msg.get("uid", "")

                if API_DEBUG: print("[serial] Got request:", msg)

                with engine.begin() as conn:
                    result, message, event, user_id, user_name = process_scan_tx(
                        conn, uid, GATE_ID, BOOTH_ID, DEVICE_ID, NODE_ID
                    )

                status_num = 1 if result == "PASS" else 0
                event_num  = EVENT_CODE.get(event, 0)
                resp = {
                    "t": "resp",
                    "id": req_id,
                    "mac": mac,
                    "status": status_num,
                    "ts": int(time.time()),
                    "event": event_num,                # 0=DENIED, 1=ENTRY, 2=EXIT
                    "ticket": f"T{user_id}" if user_id else None,  # placeholder; customize if needed
                    "name": user_name or "Guest"
                }
                ser.write((json.dumps(resp) + "\n").encode())
                if API_DEBUG: print("[serial] Sent response:", resp)
        except Exception as e:
            if API_DEBUG: print("[serial] Error:", e, " — retrying in 3s")
            time.sleep(3)  # backoff and retry open

@app.on_event("startup")
def start_serial_worker():
    # Launch background UART reader if configured
    t = threading.Thread(target=_serial_loop, daemon=True)
    t.start()
