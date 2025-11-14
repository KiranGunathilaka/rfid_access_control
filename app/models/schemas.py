
# =======================================================================================
# app/models/schemas.py - Pydantic Models
# =======================================================================================
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from .enums import UserType, EventType, ResultType, SyncStatus

# ========== Base Func + Logic ==========
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

# ========== Admin Auth ==========

class AdminAuthRequest(BaseModel):
    username: str
    password: str


class AdminInfo(BaseModel):
    id: int
    username: str


class AdminAuthResponse(BaseModel):
    token: Optional[str] = None
    message: Optional[str] = None
    admin: Optional[AdminInfo] = None


# ========== Health for dashboard ==========

class HealthResponse(BaseModel):
    status: str                 # "ok" | "error" | "offline"
    dataAvailable: bool
    message: Optional[str] = None


# ========== Analytics ==========

class Summary(BaseModel):
    total_users: int
    in_users: int
    out_users: int
    idle_users: int


class AnalyticsResponse(BaseModel):
    summary: Summary


# ========== Logs ==========

class LogUser(BaseModel):
    id: int
    name: Optional[str] = None
    nic: Optional[str] = None
    rfidTag: Optional[str] = None
    status: Optional[str] = None
    isActive: bool = True


class LogItem(BaseModel):
    id: int
    userId: Optional[int] = None
    eventType: str              # "IN" | "OUT" | "UNKNOWN"
    gateLocation: str
    deviceId: str
    timestamp: datetime
    result: str                 # "GRANTED" | "DENIED" | "UNKNOWN"
    message: Optional[str] = ""
    user: Optional[LogUser] = None


class LogsResponse(BaseModel):
    logs: List[LogItem]


# ========== User search + update for modal ==========

class SimpleUser(BaseModel):
    id: int
    name: Optional[str] = None
    nic: Optional[str] = None
    rfidTag: Optional[str] = None
    status: Optional[str] = None
    isActive: bool = True


class UserSearchResponse(BaseModel):
    success: bool
    data: List[SimpleUser]


class UserUpdateRequest(BaseModel):
    # identifier
    nic: Optional[str] = None
    rfidTag: Optional[str] = None

    # fields that can change
    status: Optional[str] = Field(
        None, description="IDLE | IN | OUT"
    )
    isActive: Optional[bool] = None
    newRfidTag: Optional[str] = None

class UserUpdateResponse(BaseModel):
    success: bool
    message: str
