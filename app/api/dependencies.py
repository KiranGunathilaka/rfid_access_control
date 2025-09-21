# =======================================================================================
# app/api/dependencies.py - FastAPI Dependencies
# =======================================================================================
from fastapi import Depends, HTTPException
from sqlalchemy.engine import Connection
from ..database import db_manager

def get_db_connection() -> Connection:
    """Dependency to get database connection."""
    try:
        with db_manager.get_connection() as conn:
            yield conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")