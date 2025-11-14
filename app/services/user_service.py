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
from ..models.schemas import UserUpdateRequest, UserUpdateResponse

class UserService:
    """Handles user management operations."""

    # ----------------- helper -----------------
    # this is to derive isActive from UserStatus (previous implementation had seperate coulm/ mine has Banned status in the userStatus)

    @staticmethod
    def is_active_from_status(status: str | None) -> bool:
        # Your rule: ONLY 'Banned' means inactive
        return status != "Banned"

    @staticmethod
    def normalize_status_for_ui(status: str | None) -> str | None:
        if status is None:
            return None
        status = status.strip()
        if status in ("In", "Out"):
            return status.upper()
        return status.upper()

    
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
    
    def search_users(self, conn: Connection, query: str) -> List[Dict[str, Any]]:
        """
        Search by NIC or RFID tag.
        Returns list of dicts that will be turned into SimpleUser.
        """
        # First: exact NIC/RFID match
        rows = conn.execute(
            text(
                """
                SELECT id, name, nic, rfid_tag, status
                FROM users
                WHERE nic = :q OR rfid_tag = :q
                ORDER BY id DESC
                LIMIT 10
                """
            ),
            {"q": query},
        ).mappings().all()

        # Fallback: partial match
        if not rows:
            like = f"%{query}%"
            rows = conn.execute(
                text(
                    """
                    SELECT id, name, nic, rfid_tag, status
                    FROM users
                    WHERE nic LIKE :like OR rfid_tag LIKE :like
                    ORDER BY id DESC
                    LIMIT 10
                    """
                ),
                {"like": like},
            ).mappings().all()

        results: List[Dict[str, Any]] = []
        for r in rows:
            status_raw = r["status"]
            results.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "nic": r["nic"],
                    "rfidTag": r["rfid_tag"],
                    "status": self.normalize_status_for_ui(status_raw),
                    "isActive": self.is_active_from_status(status_raw),
                }
            )
        return results

    # -------------- manual override used by UserManagementModal -------------- #

    def update_user_manual(
        self, conn: Connection, req: UserUpdateRequest
    ) -> UserUpdateResponse:
        """
        Manual override for status / active state / (optionally) RFID.
        isActive is mapped to status:
          - isActive = False -> status = 'Banned'
          - isActive = True  -> if currently 'Banned', set 'IDLE'
        """
        # --- identify user ---
        if not req.nic and not req.rfidTag:
            return UserUpdateResponse(success=False, message="NIC or RFID tag is required")

        where_clauses = []
        params: Dict[str, Any] = {}
        if req.nic:
            where_clauses.append("nic = :nic")
            params["nic"] = req.nic
        if req.rfidTag:
            where_clauses.append("rfid_tag = :rfid")
            params["rfid"] = req.rfidTag

        user = conn.execute(
            text(
                f"""
                SELECT id, status, rfid_tag
                FROM users
                WHERE {" OR ".join(where_clauses)}
                LIMIT 1
                """
            ),
            params,
        ).mappings().first()

        if not user:
            return UserUpdateResponse(success=False, message="User not found")

        current_status: str = user["status"]
        fields_to_set: List[str] = []
        update_params: Dict[str, Any] = {"id": user["id"]}

        # --- 1) explicit status update from Status tab (IN/OUT/IDLE) ---
        if req.status is not None:
            # Frontend sends "IN" | "OUT" | "IDLE"
            s = req.status.upper()
            if s == "IN":
                db_status = "In"
            elif s == "OUT":
                db_status = "Out"
            else:
                db_status = "IDLE"

            fields_to_set.append("status = :status")
            update_params["status"] = db_status

        # --- 2) active toggle from Active tab (only if status NOT already being set) ---
        elif req.isActive is not None:
            desired_active = bool(req.isActive)
            currently_active = self.is_active_from_status(current_status)

            # nothing to change
            if desired_active == currently_active:
                return UserUpdateResponse(success=True, message="No changes required")

            # Active -> Inactive → status = 'Banned'
            if not desired_active and currently_active:
                fields_to_set.append("status = :status")
                update_params["status"] = "Banned"

            # Inactive -> Active → if 'Banned', set 'IDLE'
            elif desired_active and not currently_active:
                fields_to_set.append("status = :status")
                update_params["status"] = "IDLE"

        # --- 3) RFID change (optional for later, if you wire frontend) ---
        if getattr(req, "newRfidTag", None):
            fields_to_set.append("rfid_tag = :new_rfid")
            update_params["new_rfid"] = req.newRfidTag

        if not fields_to_set:
            return UserUpdateResponse(success=True, message="No fields to update")

        conn.execute(
            text(
                f"""
                UPDATE users
                SET {", ".join(fields_to_set)}
                WHERE id = :id
                """
            ),
            update_params,
        )

        return UserUpdateResponse(success=True, message="User updated successfully")