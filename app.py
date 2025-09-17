import os
from typing import Optional, Literal, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import csv
import io

# -------------------------------------------------------
# Config & DB
# -------------------------------------------------------
load_dotenv()

DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:password@127.0.0.1:3306/rfid_access_control")
API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"

# Pooled engine; FastAPI can run sync DB work safely in threadpool
engine: Engine = create_engine(
    DB_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    isolation_level="READ COMMITTED",   # sane default for this workload
    future=True,
)

app = FastAPI(title="RFID Access Control API", version="1.0")

# -------------------------------------------------------
# Models
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
# Helpers
# -------------------------------------------------------
def _determine_event(current_status: UserStatus) -> tuple[EventType, UserStatus]:
    """
    Mirror of your earlier stored-proc logic:
    - IDLE/Out -> ENTRY -> becomes In
    - In       -> EXIT  -> becomes Out
    """
    if current_status in ("IDLE", "Out"):
        return "ENTRY", "In"
    elif current_status == "In":
        return "EXIT", "Out"
    else:
        # For Expired/Banned we do not call this; caller guards it.
        return "DENIED", current_status  # fallback

def _enforce_direction(gate_type: GateType, event: EventType) -> bool:
    if gate_type == "Common_IN" and event == "EXIT":
        return False
    if gate_type == "Common_Out" and event == "ENTRY":
        return False
    return True

def _enforce_gate_audience(gate_type: GateType, user_type: UserType) -> bool:
    """
    Policy:
    - VIP gate: only VIP users
    - Backstage gate: only Backstage users
    - Common_IN/Common_Out: allow any user_type
    Adjust if you want different behavior.
    """
    if gate_type == "VIP":
        return user_type == "VIP"
    if gate_type == "Backstage":
        return user_type == "Backstage"
    return True

# -------------------------------------------------------
# Endpoints
# -------------------------------------------------------
@app.post("/api/scan", response_model=ScanOut)
def handle_scan(payload: ScanIn):
    """
    Main entrypoint from the Raspberry Pi:
    - Validates booth/device/node layout (booth belongs to gate, device wired to booth & same gate, node on that gate)
    - Looks up user by RFID
    - Checks Banned/Expired
    - Computes intended event (ENTRY/EXIT)
    - Enforces directional gates and VIP/Backstage audience
    - Updates user row (status + last_* fields), inserts log row
    - Returns PASS/FAIL + message + event_type
    """
    with engine.begin() as conn:
        # 1) Validate booth & device & node topology against gate
        booth = conn.execute(
            text("SELECT gate_id, device_id FROM booths WHERE id=:bid"),
            {"bid": payload.booth_id}
        ).mappings().first()
        if not booth or booth["gate_id"] != payload.gate_id:
            _msg = "Topology error: booth does not belong to gate"
            _log_denied(conn, None, "Common", payload, _msg)
            raise HTTPException(status_code=400, detail=_msg)
        if booth["device_id"] != payload.device_id:
            _msg = "Topology error: device not assigned to booth"
            _log_denied(conn, None, "Common", payload, _msg)
            raise HTTPException(status_code=400, detail=_msg)

        dev = conn.execute(
            text("SELECT gate_id FROM devices WHERE id=:did"),
            {"did": payload.device_id}
        ).mappings().first()
        if not dev or dev["gate_id"] != payload.gate_id:
            _msg = "Topology error: device not wired to gate"
            _log_denied(conn, None, "Common", payload, _msg)
            raise HTTPException(status_code=400, detail=_msg)

        node = conn.execute(
            text("SELECT gate_id FROM nodes WHERE id=:nid"),
            {"nid": payload.node_id}
        ).mappings().first()
        if not node or node["gate_id"] != payload.gate_id:
            _msg = "Topology error: node not mounted at gate"
            _log_denied(conn, None, "Common", payload, _msg)
            raise HTTPException(status_code=400, detail=_msg)

        gate = conn.execute(
            text("SELECT type FROM gates WHERE id=:gid"),
            {"gid": payload.gate_id}
        ).mappings().first()
        if not gate:
            _msg = "Invalid gate"
            _log_denied(conn, None, "Common", payload, _msg)
            raise HTTPException(status_code=400, detail=_msg)
        gate_type: GateType = gate["type"]

        # 2) Lookup user row *with row lock* to avoid race on status toggles
        user = conn.execute(
            text("""
                SELECT id, user_type, status
                FROM users
                WHERE rfid_tag=:tag
                FOR UPDATE
            """),
            {"tag": payload.rfid_tag}
        ).mappings().first()

        if not user:
            # Unknown card: log DENIED with NULL user_id, user_type 'Common' to satisfy NOT NULL
            msg = "Unknown RFID tag"
            conn.execute(
                text("""
                    INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (NULL, :user_type, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)
                """),
                {"user_type": "Common", "gate": payload.gate_id, "booth": payload.booth_id, "msg": msg, "node": payload.node_id}
            )
            return ScanOut(result="FAIL", message=msg, event_type="DENIED")

        user_id = user["id"]
        user_type: UserType = user["user_type"]
        status: UserStatus = user["status"]

        # 3) Deny banned/expired
        if status in ("Banned", "Expired"):
            msg = f"Access denied - {status}"
            conn.execute(
                text("""
                    INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)
                """),
                {"uid": user_id, "ut": user_type, "gate": payload.gate_id, "booth": payload.booth_id, "msg": msg, "node": payload.node_id}
            )
            return ScanOut(result="FAIL", message=msg, event_type="DENIED")

        # 4) Determine intended event
        event, new_status = _determine_event(status)

        # 5) Enforce direction and audience
        if not _enforce_direction(gate_type, event):
            msg = "Wrong direction for this gate"
            conn.execute(
                text("""
                    INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)
                """),
                {"uid": user_id, "ut": user_type, "gate": payload.gate_id, "booth": payload.booth_id, "msg": msg, "node": payload.node_id}
            )
            return ScanOut(result="FAIL", message=msg, event_type="DENIED")

        if not _enforce_gate_audience(gate_type, user_type):
            msg = f"Access denied - gate restricted to {gate_type}"
            conn.execute(
                text("""
                    INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)
                """),
                {"uid": user_id, "ut": user_type, "gate": payload.gate_id, "booth": payload.booth_id, "msg": msg, "node": payload.node_id}
            )
            return ScanOut(result="FAIL", message=msg, event_type="DENIED")

        # 6) Update user + insert log (atomic)
        conn.execute(
            text("""
                UPDATE users
                SET status=:new_status,
                    last_seen_at=CURRENT_TIMESTAMP,
                    last_gate_id=:gate,
                    last_booth_id=:booth,
                    last_result='PASS',
                    node_id=:node
                WHERE id=:uid
            """),
            {"new_status": new_status, "gate": payload.gate_id, "booth": payload.booth_id, "node": payload.node_id, "uid": user_id}
        )

        conn.execute(
            text("""
                INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                VALUES (:uid, :ut, :evt, :gate, :booth, 'PASS', :msg, :node)
            """),
            {"uid": user_id, "ut": user_type, "evt": event, "gate": payload.gate_id, "booth": payload.booth_id,
             "msg": f"Access granted - {event}", "node": payload.node_id}
        )

        return ScanOut(result="PASS", message=f"Access granted - {event}", event_type=event)

def _log_denied(conn, user_id: Optional[int], user_type: UserType, payload: ScanIn, msg: str):
    conn.execute(
        text("""
            INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
            VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)
        """),
        {"uid": user_id, "ut": user_type, "gate": payload.gate_id, "booth": payload.booth_id, "msg": msg, "node": payload.node_id}
    )

# -------- Users --------
@app.post("/api/users", response_model=CreateUserOut)
def create_user(body: CreateUserIn):
    """
    Create a user from backend (used by manual entry or your admin tool).
    Starts as IDLE; rfid_tag is UNIQUE per schema.
    """
    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("""
                    INSERT INTO users (rfid_tag, name, nic, user_type, status)
                    VALUES (:tag, :name, :nic, :ut, 'IDLE')
                """),
                {"tag": body.rfid_tag, "name": body.name, "nic": body.nic, "ut": body.user_type}
            )
            new_id = res.lastrowid
            return CreateUserOut(id=new_id, success=True, message="User added")
    except Exception as e:
        # likely duplicate RFID
        if API_DEBUG:
            print("create_user error:", e)
        return CreateUserOut(id=None, success=False, message="RFID tag already exists or DB error")

@app.post("/api/users/import")
def import_users(file: UploadFile = File(...)):
    """
    CSV import: headers = rfid_tag,name,nic,user_type
    Example line: RFID001,John Doe,123456789V,Common
    """
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
                    text("""
                        INSERT INTO users (rfid_tag, name, nic, user_type, status)
                        VALUES (:tag, :name, :nic, :ut, 'IDLE')
                    """),
                    {
                        "tag": row.get("rfid_tag","").strip(),
                        "name": (row.get("name") or None),
                        "nic": (row.get("nic") or None),
                        "ut": (row.get("user_type") or "Common").strip() or "Common",
                    }
                )
                inserted += 1
            except Exception:
                duplicates += 1
                # We no longer write to replication_conflicts for user duplicates
                # because that table now FKs to logs.id (conflicts are about logs).
                continue

    return {"inserted": inserted, "duplicates": duplicates}

# -------- Sync Status --------
@app.get("/api/sync/status", response_model=List[SyncStatusRow])
def sync_status():
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT node_id, table_name, last_sync_timestamp, sync_status, error_message,
                       TIMESTAMPDIFF(MINUTE, last_sync_timestamp, NOW()) AS minutes_since_sync
                FROM sync_status_view
                ORDER BY node_id, table_name
            """)
        ).mappings().all()
        return [SyncStatusRow(**row) for row in rows]
