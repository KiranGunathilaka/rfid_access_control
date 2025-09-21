# =======================================================================================
# app/services/sync_service.py - Database Synchronization Service
# =======================================================================================
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Connection
from ..models.schemas import SyncStatusRow

class SyncService:
    """Handles database synchronization between nodes."""
    
    def get_sync_status(self, conn: Connection) -> List[SyncStatusRow]:
        """Get synchronization status for all nodes."""
        rows = conn.execute(
            text("""
                SELECT node_id, table_name, last_sync_timestamp, sync_status, 
                       error_message, TIMESTAMPDIFF(MINUTE, last_sync_timestamp, NOW()) AS minutes_since_sync
                FROM sync_status_view
                ORDER BY node_id, table_name
            """)
        ).mappings().all()
        
        return [SyncStatusRow(**row) for row in rows]
    
    def trigger_manual_sync(self, conn: Connection, node_id: Optional[int] = None) -> Dict[str, Any]:
        """Trigger manual synchronization for a specific node or all nodes."""
        # Implementation would depend on your sync strategy
        # This is a placeholder for the sync trigger logic
        
        if node_id:
            # Trigger sync for specific node
            conn.execute(
                text("""
                    UPDATE sync_metadata 
                    SET sync_status = 'IN_PROGRESS', last_sync_timestamp = NOW() 
                    WHERE node_id = :nid
                """),
                {"nid": node_id}
            )
            return {"message": f"Sync triggered for node {node_id}", "node_id": node_id}
        else:
            # Trigger sync for all nodes
            conn.execute(
                text("""
                    UPDATE sync_metadata 
                    SET sync_status = 'IN_PROGRESS', last_sync_timestamp = NOW()
                """)
            )
            return {"message": "Sync triggered for all nodes"}