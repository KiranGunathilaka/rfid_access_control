# =======================================================================================
# app/services/dashboard_service.py
# =======================================================================================

from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Connection


class DashboardService:
    """Aggregated analytics and logs for the dashboard."""

    # ---------- helper mapping ----------

    def map_event_type(self, db_event: str | None) -> str:
        if db_event == "ENTRY":
            return "IN"
        if db_event == "EXIT":
            return "OUT"
        return "UNKNOWN"

    def map_result(self, db_result: str | None) -> str:
        if db_result == "PASS":
            return "GRANTED"
        if db_result == "FAIL":
            return "DENIED"
        return "UNKNOWN"

    def normalize_status_for_ui(self, status: str | None) -> str | None:
        """
        Map DB status to UI-friendly string.
        DB: 'In', 'Out', 'IDLE', 'Expired', 'Banned'
        UI: 'IN', 'OUT', 'IDLE', 'EXPIRED', 'BANNED'
        """
        if status is None:
            return None
        status = status.strip()
        if status in ("In", "Out"):
            return status.upper()
        return status.upper()

    def is_active_from_status(self, status: str | None) -> bool:
        """
        Your rule: if status == 'Banned' -> isActive = False.
        Everything else is considered active.
        """
        return status != "Banned"

    # ---------- summary ----------

    def get_summary(self, conn: Connection) -> Dict[str, int]:
        row = conn.execute(
            text(
                """
                SELECT 
                  COUNT(*) AS total_users,
                  SUM(status = 'In')    AS in_users,
                  SUM(status = 'Out')   AS out_users,
                  SUM(status = 'IDLE')  AS idle_users
                FROM users
                """
            )
        ).mappings().first()

        if not row:
            return {"total_users": 0, "in_users": 0, "out_users": 0, "idle_users": 0}

        return {
            "total_users": int(row["total_users"] or 0),
            "in_users": int(row["in_users"] or 0),
            "out_users": int(row["out_users"] or 0),
            "idle_users": int(row["idle_users"] or 0),
        }

    # ---------- logs ----------

    def get_logs(self, conn: Connection, limit: int = 1000) -> List[Dict[str, Any]]:
        rows = conn.execute(
            text(
                """
                SELECT
                    l.id            AS log_id,
                    l.user_id       AS user_id,
                    l.event_type    AS event_type,
                    l.timestamp     AS ts,
                    l.result        AS db_result,
                    l.message       AS msg,
                    g.gate_name     AS gate_name,
                    b.booth_name    AS booth_name,
                    d.device_id     AS device_identifier,
                    u.id            AS u_id,
                    u.name          AS u_name,
                    u.nic           AS u_nic,
                    u.rfid_tag      AS u_rfid,
                    u.status        AS u_status
                FROM logs l
                LEFT JOIN gates   g ON l.gate_id = g.id
                LEFT JOIN booths  b ON l.booth_id = b.id
                LEFT JOIN devices d ON b.device_id = d.id
                LEFT JOIN users   u ON l.user_id = u.id
                ORDER BY l.timestamp DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

        logs: List[Dict[str, Any]] = []

        for row in rows:
            gate_location = row["gate_name"] or "Unknown gate"
            if row["booth_name"]:
                gate_location = f"{row['gate_name']} / {row['booth_name']}"

            user = None
            if row["u_id"] is not None:
                status_raw = row["u_status"]
                user = {
                    "id": row["u_id"],
                    "name": row["u_name"],
                    "nic": row["u_nic"],
                    "rfidTag": row["u_rfid"],
                    "status": self.normalize_status_for_ui(status_raw),
                    "isActive": self.is_active_from_status(status_raw),
                }

            logs.append(
                {
                    "id": row["log_id"],
                    "userId": row["user_id"],
                    "eventType": self.map_event_type(row["event_type"]),
                    "gateLocation": gate_location,
                    "deviceId": row["device_identifier"] or "N/A",
                    "timestamp": row["ts"],
                    "result": self.map_result(row["db_result"]),
                    "message": row["msg"],
                    "user": user,
                }
            )

        return logs
