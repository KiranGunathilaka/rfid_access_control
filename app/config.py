# =======================================================================================
# app/config.py - Configuration Management
# =======================================================================================
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

def _env_int(name: str) -> Optional[int]:
    """Helper to parse integer environment variables."""
    v = os.getenv(name)
    return int(v) if v and v.isdigit() else None

class Config:
    # Database
    DB_URL: str = os.getenv("DB_URL", "mysql+pymysql://root:password@127.0.0.1:3306/rfid_access_control")
    
    # API Settings
    API_DEBUG: bool = os.getenv("API_DEBUG", "false").lower() == "true"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Serial Communication
    SERIAL_PORT: str = os.getenv("SERIAL_PORT", "/dev/ttyACM0")
    SERIAL_BAUD: int = int(os.getenv("SERIAL_BAUD", "115200"))
    SERIAL_TIMEOUT: int = int(os.getenv("SERIAL_TIMEOUT", "1"))
    
    # Node Configuration
    NODE_ID: Optional[int] = _env_int("NODE_ID")
    GATE_ID: Optional[int] = _env_int("GATE_ID")
    BOOTH_ID: Optional[int] = _env_int("BOOTH_ID")
    DEVICE_ID: Optional[int] = _env_int("DEVICE_ID")
    
    # Database Connection Pool
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    
    # Sync Settings
    SYNC_RETRY_ATTEMPTS: int = int(os.getenv("SYNC_RETRY_ATTEMPTS", "3"))
    SYNC_RETRY_DELAY: int = int(os.getenv("SYNC_RETRY_DELAY", "5"))

config = Config()