# app/services/serial_service.py
import time
from collections import OrderedDict
from typing import Optional, Dict, Any, Tuple
from ..models.schemas import SerialMessage
from ..models.enums import EventCode
from ..services.access_control import AccessControlService
from ..database import db_manager
from ..config import config
from ..utils.validators import TopologyValidator
from ..utils.exceptions import TopologyError


class SerialService:
    """Handles serial communication with ESP32 devices and RFID requests."""

    def __init__(self):
        self.access_service = AccessControlService()
        self.topology_validator = TopologyValidator()

        # Event code mapping for clarity
        self.event_codes = {
            "DENIED": EventCode.DENIED.value,
            "ENTRY": EventCode.ENTRY.value,
            "EXIT": EventCode.EXIT.value,
        }

        # ----------------------------------------------------------------------
        # Debounce cache
        # ----------------------------------------------------------------------
        # key = (uid, dev_code, gate_id, node_id)
        # value = (timestamp, (result, event, user_id, user_name))
        self._scan_cache: "OrderedDict[tuple, tuple]" = OrderedDict()
        self._scan_cache_ttl = 0.5     # seconds (treat all reads within this as one scan)
        self._scan_cache_max = 512   # avoid unbounded growth

    # ----------------------------------------------------------------------
    # Cache helpers
    # ----------------------------------------------------------------------
    def _get_cached_decision(
        self, key: tuple
    ) -> Optional[Tuple[str, str, Optional[int], Optional[str]]]:
        """Return cached decision if still valid."""
        item = self._scan_cache.get(key)
        if not item:
            return None

        ts, decision = item
        if time.time() - ts > self._scan_cache_ttl:
            self._scan_cache.pop(key, None)
            return None

        # keep most-recently-used ordering
        self._scan_cache.move_to_end(key)
        return decision

    def _store_decision(
        self, key: tuple, decision: Tuple[str, str, Optional[int], Optional[str]]
    ) -> None:
        """Store decision with timestamp and trim cache size."""
        self._scan_cache[key] = (time.time(), decision)
        while len(self._scan_cache) > self._scan_cache_max:
            self._scan_cache.popitem(last=False)

    # ----------------------------------------------------------------------
    # Core request handler
    # ----------------------------------------------------------------------
    def process_rfid_request(self, message: SerialMessage) -> Optional[Dict[str, Any]]:
        """Process a single RFID scan request from ESP32 hub."""
        if message.t != "req" or not all([message.uid, message.dev_id]):
            return None

        gate_id = config.GATE_ID
        node_id = config.NODE_ID
        if gate_id is None or node_id is None:
            if config.API_DEBUG:
                print("[serial] Missing GATE_ID or NODE_ID; cannot process request.")
            return self.create_response_message(message, "FAIL", "DENIED", None, None)

        # Normalize dev_id
        try:
            dev_code = int(message.dev_id)
        except (TypeError, ValueError):
            if config.API_DEBUG:
                print(f"[serial] Invalid dev_id in message: {message.dev_id}")
            return self.create_response_message(message, "FAIL", "DENIED", None, None)

        cache_key = (message.uid, dev_code, gate_id, node_id)
        cached = self._get_cached_decision(cache_key)
        if cached is not None:
            result, event, user_id, user_name = cached
            if config.API_DEBUG:
                print(f"[serial] Using cached decision for uid={message.uid}, dev={dev_code}")
            return self.create_response_message(message, result, event, user_id, user_name)

        # ------------------------------------------------------------
        # No cached result → full DB pipeline
        # ------------------------------------------------------------
        try:
            with db_manager.get_connection() as conn:
                # Resolve device + booth topology
                try:
                    device_db_id, booth_id = self.topology_validator.resolve_booth_for_device_code(
                        conn, gate_id, dev_code
                    )
                except TopologyError as te:
                    if config.API_DEBUG:
                        print(f"[serial] Topology error for dev_id={dev_code}: {te}")
                    decision = ("FAIL", "DENIED", None, None)
                    self._store_decision(cache_key, decision)
                    return self.create_response_message(message, *decision)

                # Run access control logic
                result, msg, event, user_id, user_name = self.access_service.process_access_request(
                    conn,
                    message.uid,
                    gate_id,
                    booth_id,
                    device_db_id,
                    node_id,
                )

            decision = (result, event, user_id, user_name)
            self._store_decision(cache_key, decision)
            return self.create_response_message(message, result, event, user_id, user_name)

        except Exception as e:
            if config.API_DEBUG:
                print(f"[serial] Error processing request: {e}")
            decision = ("FAIL", "DENIED", None, None)
            self._store_decision(cache_key, decision)
            return self.create_response_message(message, *decision)

    # ----------------------------------------------------------------------
    # Response builder
    # ----------------------------------------------------------------------
    def create_response_message(
        self,
        message: SerialMessage,
        result: str,
        event: str,
        user_id: Optional[int],
        user_name: Optional[str],
    ) -> Dict[str, Any]:
        """Generate JSON-serializable dict to send to ESP."""
        return {
            "t": "resp",
            "id": message.id,
            "mac": message.mac,
            "status": 1 if result == "PASS" else 0,
            "ts": int(time.time()),
            "event": self.event_codes.get(event.upper(), 0),
            "ticket": f"T{user_id}" if user_id else None,
            "name": user_name or "Guest",
        }
