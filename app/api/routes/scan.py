# =======================================================================================
# app/api/routes/scan.py - Scan Endpoints
# =======================================================================================
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Connection
from ...models.schemas import ScanRequest, ScanResponse
from ...services.access_control import AccessControlService
from ..dependencies import get_db_connection

router = APIRouter()
access_service = AccessControlService()

@router.post("/scan", response_model=ScanResponse)
def handle_scan(request: ScanRequest, conn: Connection = Depends(get_db_connection)):
    """Process RFID scan request."""
    try:
        result, message, event, user_id, user_name = access_service.process_access_request(
            conn, request.rfid_tag, request.gate_id, request.booth_id, 
            request.device_id, request.node_id
        )
        
        if result == "FAIL":
            raise HTTPException(status_code=400, detail=message)
        
        return ScanResponse(
            result=result,
            message=message,
            event_type=event,
            user_id=user_id,
            user_name=user_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))