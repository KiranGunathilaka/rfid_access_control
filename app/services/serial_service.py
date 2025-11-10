# =======================================================================================
# app/services/serial_service.py - Serial Communication Service
# =======================================================================================
import json
import time
from typing import Optional, Dict, Any
from ..models.schemas import SerialMessage
from ..models.enums import EventCode
from ..services.access_control import AccessControlService
from ..database import db_manager
from ..config import config
from ..utils.validators import TopologyValidator       
from ..utils.exceptions import TopologyError    

class SerialService:
    """Handles serial communication with ESP32 devices."""
    
    def __init__(self):
        self.access_service = AccessControlService()
        self.topology_validator = TopologyValidator()   # ⬅️ NEW
        self.event_codes = {
            "DENIED": EventCode.DENIED.value,
            "ENTRY": EventCode.ENTRY.value,
            "EXIT": EventCode.EXIT.value
        }
    
    def parse_serial_message(self, line: str) -> Optional[SerialMessage]:
        """Parse incoming serial message."""
        try:
            data = json.loads(line)
            return SerialMessage(**data)
        except (json.JSONDecodeError, ValueError) as e:
            if config.API_DEBUG:
                print(f"[serial] Failed to parse message: {line}, error: {e}")
            return None
    
    def process_rfid_request(self, message: SerialMessage) -> Optional[Dict[str, Any]]:
        """Process RFID request from ESP32."""
        if message.t != "req" or not all([message.uid, message.dev_id]):
            return None

        gate_id = config.GATE_ID
        node_id = config.NODE_ID

        if gate_id is None or node_id is None:
            if config.API_DEBUG:
                print("[serial] Missing GATE_ID or NODE_ID in config; cannot process request")
            # respond with a generic failure so the ESP gives user feedback
            return self.create_response_message(
                message, "FAIL", "DENIED", None, None
            )

        try:
            with db_manager.get_connection() as conn:
                # 1) Resolve physical dev_code -> (devices.id, booths.id)
                try:
                    device_db_id, booth_id = self.topology_validator.resolve_booth_for_device_code(
                        conn, gate_id, int(message.dev_id)
                    )
                except TopologyError as te:
                    # Device/booth mis-configured or unknown: fail gracefully
                    if config.API_DEBUG:
                        print(f"[serial] Topology error for dev_id={message.dev_id}: {te}")
                    return self.create_response_message(
                        message, "FAIL", "DENIED", None, None
                    )

                # 2) Run full access control pipeline
                result, msg, event, user_id, user_name = self.access_service.process_access_request(
                    conn,
                    message.uid,
                    gate_id,
                    booth_id,
                    device_db_id,
                    node_id,
                )

            # 3) Build response JSON for ESP
            return self.create_response_message(
                message, result, event, user_id, user_name
            )

        except Exception as e:
            if config.API_DEBUG:
                print(f"[serial] Error processing request: {e}")
            # On unexpected error, return a DENIED response instead of None,
            # so the ESP can still give a visible/audible error.
            return self.create_response_message(
                message, "FAIL", "DENIED", None, None
            )
    
    def create_response_message(self, request: SerialMessage, result: str, 
                              event: str, user_id: Optional[int], 
                              user_name: Optional[str]) -> Dict[str, Any]:
        """Create response message for ESP32."""
        status_num = 1 if result == "PASS" else 0
        event_num = self.event_codes.get(event, 0)
        
        return {
            "t": "resp",
            "id": request.id,
            "mac": request.mac,
            "status": status_num,
            "ts": int(time.time()),
            "event": event_num,
            "ticket": f"T{user_id}" if user_id else None,
            "name": user_name or "Guest"
        }
