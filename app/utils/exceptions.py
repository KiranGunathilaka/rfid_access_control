# =======================================================================================
# app/utils/exceptions.py - Custom Exceptions
# =======================================================================================
class RFIDAccessControlError(Exception):
    """Base exception for RFID access control system."""
    pass

class TopologyError(RFIDAccessControlError):
    """Raised when there's a topology validation error."""
    pass

class AccessDeniedError(RFIDAccessControlError):
    """Raised when access is denied."""
    pass

class UserNotFoundError(RFIDAccessControlError):
    """Raised when a user is not found."""
    pass

class InvalidGateError(RFIDAccessControlError):
    """Raised when gate information is invalid."""
    pass