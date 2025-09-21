# =======================================================================================
# app/services/user_service.py - User Management Service
# =======================================================================================
import io
import csv
from typing import Optional, List, Dict, Any
from fastapi import UploadFile, HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection
from ..models.schemas import CreateUserRequest, CreateUserResponse
from ..config import config

class UserService:
    """Handles user management operations."""
    
    def create_user(self, conn: Connection, request: CreateUserRequest) -> CreateUserResponse:
        """Create a new user in the system."""
        try:
            result = conn.execute(
                text("""
                    INSERT INTO users (rfid_tag, name, nic, user_type, status)
                    VALUES (:tag, :name, :nic, :ut, 'IDLE')
                """),
                {
                    "tag": request.rfid_tag,
                    "name": request.name,
                    "nic": request.nic,
                    "ut": request.user_type
                }
            )
            
            return CreateUserResponse(
                id=result.lastrowid,
                success=True,
                message="User created successfully"
            )
            
        except Exception as e:
            if config.API_DEBUG:
                print(f"Create user error: {e}")
            return CreateUserResponse(
                id=None,
                success=False,
                message="RFID tag already exists or database error"
            )
    
    def import_users_from_csv(self, conn: Connection, file: UploadFile) -> Dict[str, int]:
        """Import users from CSV file."""
        inserted = 0
        duplicates = 0
        
        try:
            data = file.file.read()
            text_stream = io.StringIO(data.decode("utf-8"))
            reader = csv.DictReader(text_stream)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid CSV encoding")
        
        for row in reader:
            try:
                conn.execute(
                    text("""
                        INSERT INTO users (rfid_tag, name, nic, user_type, status)
                        VALUES (:tag, :name, :nic, :ut, 'IDLE')
                    """),
                    {
                        "tag": (row.get("rfid_tag") or "").strip(),
                        "name": row.get("name") or None,
                        "nic": row.get("nic") or None,
                        "ut": (row.get("user_type") or "Common").strip() or "Common"
                    }
                )
                inserted += 1
            except Exception:
                duplicates += 1
                continue
        
        return {"inserted": inserted, "duplicates": duplicates}
    
    def get_user_by_id(self, conn: Connection, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        user = conn.execute(
            text("SELECT * FROM users WHERE id = :uid"),
            {"uid": user_id}
        ).mappings().first()
        
        return dict(user) if user else None
    
    def list_users(self, conn: Connection, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List users with pagination."""
        users = conn.execute(
            text("SELECT * FROM users ORDER BY created_at DESC LIMIT :limit OFFSET :skip"),
            {"limit": limit, "skip": skip}
        ).mappings().all()
        
        return [dict(user) for user in users]