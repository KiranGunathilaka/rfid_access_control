# =======================================================================================
# app/services/access_control.py - Core Business Logic
# =======================================================================================
from typing import Tuple, Optional
from sqlalchemy import text
from sqlalchemy.engine import Connection
from ..models.enums import UserType, GateType, UserStatus, EventType, ResultType
from ..utils.validators import TopologyValidator
from ..utils.exceptions import UserNotFoundError, AccessDeniedError

class AccessControlService:
    """Handles core access control business logic."""
    
    @staticmethod
    def determine_event(current_status: UserStatus) -> Tuple[EventType, UserStatus]:
        """Determine the event type and new status based on current status."""
        if current_status in ("IDLE", "Out"):
            return "ENTRY", "In"
        elif current_status == "In":
            return "EXIT", "Out"
        return "DENIED", current_status
    
    @staticmethod
    def enforce_direction(gate_type: GateType, event: EventType) -> bool:
        """Enforce directional restrictions for gates."""
        if gate_type == "Common_IN" and event == "EXIT":
            return False
        if gate_type == "Common_Out" and event == "ENTRY":
            return False
        return True
    
    @staticmethod
    def enforce_gate_audience(gate_type: GateType, user_type: UserType) -> bool:
        """Enforce user type restrictions for gates."""
        if gate_type == "VIP":
            return user_type == "VIP"
        if gate_type == "Backstage":
            return user_type == "Backstage"
        return True
    
    @staticmethod
    def log_denied_access(conn: Connection, user_id: Optional[int], user_type: UserType, 
                         gate_id: int, booth_id: int, node_id: int, message: str):
        """Log denied access attempt."""
        conn.execute(
            text("""
                INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                VALUES (:uid, :ut, 'DENIED', :gate, :booth, 'FAIL', :msg, :node)
            """),
            {
                "uid": user_id, "ut": user_type, "gate": gate_id, 
                "booth": booth_id, "msg": message, "node": node_id
            }
        )
    
    def process_access_request(self, conn: Connection, rfid_tag: str, gate_id: int, 
                             booth_id: int, device_id: int, node_id: int) -> Tuple[ResultType, str, EventType, Optional[int], Optional[str]]:
        """
        Process an access request through the complete validation pipeline.
        Returns: (result, message, event_type, user_id, user_name)
        """
        validator = TopologyValidator()
        
        try:
            # Validate topology
            validator.validate_booth_topology(conn, gate_id, booth_id, device_id)
            validator.validate_device_topology(conn, gate_id, device_id)
            validator.validate_node_topology(conn, gate_id, node_id)
            gate_type = validator.get_gate_type(conn, gate_id)
            
            # Find and lock user
            user = conn.execute(
                text("SELECT id, name, user_type, status FROM users WHERE rfid_tag=:tag FOR UPDATE"),
                {"tag": rfid_tag}
            ).mappings().first()
            
            if not user:
                self.log_denied_access(conn, None, "Common", gate_id, booth_id, node_id, "Unknown RFID tag")
                return "FAIL", "Unknown RFID tag", "DENIED", None, None
            
            user_id = user["id"]
            user_name = user["name"]
            user_type: UserType = user["user_type"]
            status: UserStatus = user["status"]
            
            # Check user status
            if status in ("Banned", "Expired"):
                message = f"Access denied - {status}"
                self.log_denied_access(conn, user_id, user_type, gate_id, booth_id, node_id, message)
                return "FAIL", message, "DENIED", user_id, user_name
            
            # Determine event and validate access
            event, new_status = self.determine_event(status)
            
            if not self.enforce_direction(gate_type, event):
                message = "Wrong direction for this gate"
                self.log_denied_access(conn, user_id, user_type, gate_id, booth_id, node_id, message)
                return "FAIL", message, "DENIED", user_id, user_name
            
            if not self.enforce_gate_audience(gate_type, user_type):
                message = f"Access denied - gate restricted to {gate_type}"
                self.log_denied_access(conn, user_id, user_type, gate_id, booth_id, node_id, message)
                return "FAIL", message, "DENIED", user_id, user_name
            
            # Grant access - update user and log success
            conn.execute(
                text("""
                    UPDATE users
                    SET status=:new_status, last_seen_at=CURRENT_TIMESTAMP,
                        last_gate_id=:gate, last_booth_id=:booth,
                        last_result='PASS', node_id=:node
                    WHERE id=:uid
                """),
                {
                    "new_status": new_status, "gate": gate_id, "booth": booth_id,
                    "node": node_id, "uid": user_id
                }
            )
            
            message = f"Access granted - {event}"
            conn.execute(
                text("""
                    INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                    VALUES (:uid, :ut, :evt, :gate, :booth, 'PASS', :msg, :node)
                """),
                {
                    "uid": user_id, "ut": user_type, "evt": event,
                    "gate": gate_id, "booth": booth_id, "msg": message, "node": node_id
                }
            )
            
            return "PASS", message, event, user_id, user_name
            
        except Exception as e:
            error_msg = str(e)
            self.log_denied_access(conn, None, "Common", gate_id, booth_id, node_id, error_msg)
            return "FAIL", error_msg, "DENIED", None, None