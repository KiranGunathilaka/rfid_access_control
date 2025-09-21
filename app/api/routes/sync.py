# =======================================================================================
# app/api/routes/sync.py - Synchronization Endpoints
# =======================================================================================
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection
from ...models.schemas import SyncStatusRow
from ...services.sync_service import SyncService
from ..dependencies import get_db_connection

router = APIRouter()
sync_service = SyncService()

@router.get("/sync/status", response_model=List[SyncStatusRow])
def get_sync_status(conn: Connection = Depends(get_db_connection)):
    """Get synchronization status for all nodes."""
    return sync_service.get_sync_status(conn)

@router.post("/sync/trigger")
def trigger_sync(node_id: int = None, conn: Connection = Depends(get_db_connection)):
    """Trigger manual synchronization."""
    return sync_service.trigger_manual_sync(conn, node_id)