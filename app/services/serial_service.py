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

class SerialService:
    """Handles serial communication with ESP32 devices."""
    
    def __init__(self):
        self.access_service = AccessControlService()
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
        
        try:
            with db_manager.get_connection() as conn:
                result, msg, event, user_id, user_name = self.access_service.process_access_request(
                    conn, message.uid, config.GATE_ID, config.BOOTH_ID, 
                    config.DEVICE_ID, config.NODE_ID
                )
            
            return self.create_response_message(
                message, result, event, user_id, user_name
            )
            
        except Exception as e:
            if config.API_DEBUG:
                print(f"[serial] Error processing request: {e}")
            return None
    
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