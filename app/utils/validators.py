# =======================================================================================
# app/utils/validators.py - Validation Helpers
# =======================================================================================
from sqlalchemy import text
from sqlalchemy.engine import Connection
from .exceptions import TopologyError, InvalidGateError
from ..models.enums import GateType

class TopologyValidator:
    """Validates system topology and relationships."""
    
    @staticmethod
    def validate_booth_topology(conn: Connection, gate_id: int, booth_id: int, device_id: int) -> bool:
        """Validate booth belongs to gate and device is assigned correctly."""
        booth = conn.execute(
            text("SELECT gate_id, device_id FROM booths WHERE id=:bid"), 
            {"bid": booth_id}
        ).mappings().first()
        
        if not booth:
            raise TopologyError("Booth not found")
        
        if booth["gate_id"] != gate_id:
            raise TopologyError("Booth does not belong to gate")
        
        if booth["device_id"] != device_id:
            raise TopologyError("Device not assigned to booth")
        
        return True
    
    @staticmethod
    def validate_device_topology(conn: Connection, gate_id: int, device_id: int) -> bool:
        """Validate device is wired to the correct gate."""
        dev = conn.execute(
            text("SELECT gate_id FROM devices WHERE id=:did"), 
            {"did": device_id}
        ).mappings().first()
        
        if not dev:
            raise TopologyError("Device not found")
        
        if dev["gate_id"] != gate_id:
            raise TopologyError("Device not wired to gate")
        
        return True
    
    @staticmethod
    def validate_node_topology(conn: Connection, gate_id: int, node_id: int) -> bool:
        """Validate node is mounted at the correct gate."""
        node = conn.execute(
            text("SELECT gate_id FROM nodes WHERE id=:nid"), 
            {"nid": node_id}
        ).mappings().first()
        
        if not node:
            raise TopologyError("Node not found")
        
        if node["gate_id"] != gate_id:
            raise TopologyError("Node not mounted at gate")
        
        return True
    
    @staticmethod
    def get_gate_type(conn: Connection, gate_id: int) -> GateType:
        """Get and validate gate type."""
        gate = conn.execute(
            text("SELECT type FROM gates WHERE id=:gid"), 
            {"gid": gate_id}
        ).mappings().first()
        
        if not gate:
            raise InvalidGateError("Invalid gate")
        
        return gate["type"]