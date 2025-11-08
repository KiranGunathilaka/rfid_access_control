
# =======================================================================================
# app/models/schemas.py - Pydantic Models
# =======================================================================================
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from .enums import UserType, EventType, ResultType, SyncStatus

class ScanRequest(BaseModel):
    """RFID scan request model."""
    rfid_tag: str = Field(..., min_length=1, max_length=100, description="RFID tag identifier")
    gate_id: int = Field(..., description="Gate ID where scan occurred")
    booth_id: int = Field(..., description="Booth ID where scan occurred")
    device_id: int = Field(..., description="Device ID that captured the scan")
    node_id: int = Field(..., description="Node ID processing the scan")

class ScanResponse(BaseModel):
    """RFID scan response model."""
    result: ResultType
    message: str
    event_type: EventType
    user_id: Optional[int] = None
    user_name: Optional[str] = None

class CreateUserRequest(BaseModel):
    """Create user request model."""
    rfid_tag: str = Field(..., description="RFID tag identifier")
    name: Optional[str] = Field(None, description="User's full name")
    nic: Optional[str] = Field(None, description="National ID number")
    user_type: UserType = Field("Common", description="User access type")

class CreateUserResponse(BaseModel):
    """Create user response model."""
    id: Optional[int]
    success: bool
    message: str

class SyncStatusRow(BaseModel):
    """Sync status information model."""
    node_id: int
    table_name: str
    last_sync_timestamp: datetime
    sync_status: SyncStatus
    error_message: Optional[str] = None
    minutes_since_sync: int

class SerialMessage(BaseModel):
    t: str
    id: Optional[int] = None   
    mac: Optional[str] = None
    dev_id: Optional[int] = None
    uid: Optional[str] = None
    status: Optional[int] = None
    ts: Optional[int] = None
    event: Optional[int] = None
    ticket: Optional[str] = None
    name: Optional[str] = None