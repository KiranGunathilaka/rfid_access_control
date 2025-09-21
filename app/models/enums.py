# =======================================================================================
# app/models/enums.py - Enums and Constants
# =======================================================================================
from enum import Enum
from typing import Literal

# Type aliases for better type hints
UserType = Literal["Common", "VIP", "Backstage"]
GateType = Literal["Common_IN", "Common_Out", "VIP", "Backstage"]
UserStatus = Literal["IDLE", "In", "Out", "Expired", "Banned"]
EventType = Literal["ENTRY", "EXIT", "DENIED"]
ResultType = Literal["PASS", "FAIL"]
SyncStatus = Literal["SUCCESS", "FAILED", "IN_PROGRESS"]

class EventCode(Enum):
    """Event codes for serial communication."""
    DENIED = 0
    ENTRY = 1
    EXIT = 2

class AccessResult(Enum):
    """Access control results."""
    PASS = "PASS"
    FAIL = "FAIL"
