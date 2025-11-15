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

# Entire thing is freaking messy cuz the front end and previous implementation isn't mine. By the time I received frontend
# I had implemented databases and everything

# Change these if DB cleared and setuped again
ADMIN_GATE_ID = 7
ADMIN_BOOTH_ID = 13
ADMIN_NODE_ID = 5


class UserService:
    """Handles user management operations."""

    # ----------------- helper -----------------
    # this is to derive isActive from UserStatus (previous implementation had seperate coulm/ mine has Banned status in the userStatus)
    @staticmethod
    def is_active_from_status(status: str | None) -> bool:
        """
        Consider 'Banned' and 'Expired' as inactive.
        Everything else (IDLE, In, Out) is active.
        """
        if status is None:
            return False
        status = status.strip()
        return status not in ("Banned", "Expired")

    @staticmethod
    def normalize_status_for_ui(status: str | None) -> str | None:
        """
        Map DB enum values -> consistent uppercase string for frontend:
        IDLE, IN, OUT, EXPIRED, BANNED
        """
        if status is None:
            return None

        status = status.strip()

        if status == "In":
            return "IN"
        if status == "Out":
            return "OUT"
        if status == "IDLE":
            return "IDLE"
        if status == "Expired":
            return "EXPIRED"
        if status == "Banned":
            return "BANNED"

        # fallback just in case
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

    # -------------- manual override used by UserManagementModal -------------- 
    def update_user_manual(
        self, conn: Connection, req: UserUpdateRequest
    ) -> UserUpdateResponse:
        """
        Manual override for status / active state / RFID.

        isActive is mapped to status:
        - isActive = False -> status = 'Banned'
        - isActive = True  -> if currently inactive (Banned/Expired), set 'IDLE'

        Also logs an admin entry in `logs` that reflects the resulting status:
        - In  -> event_type = 'ENTRY', result = 'PASS'
        - Out -> event_type = 'EXIT',  result = 'PASS'
        - IDLE -> event_type = 'ENTRY', result = 'PASS' (neutral reset, explained in message)
        - Banned/Expired -> event_type = 'DENIED', result = 'FAIL'
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
                SELECT id, status, rfid_tag, user_type
                FROM users
                WHERE {" OR ".join(where_clauses)}
                LIMIT 1
                """
            ),
            params,
        ).mappings().first()

        if not user:
            return UserUpdateResponse(success=False, message="User not found")

        user_id: int = user["id"]
        current_status: str = user["status"]   # DB status: 'IDLE', 'In', 'Out', 'Expired', 'Banned'
        current_rfid: str = user["rfid_tag"]
        user_type = user["user_type"]

        fields_to_set: List[str] = []
        update_params: Dict[str, Any] = {"id": user_id}

        # --- 1) explicit status update from Status tab (IN/OUT/IDLE) ---
        if req.status is not None:
            s = req.status.upper()
            if s == "IN":
                db_status = "In"
            elif s == "OUT":
                db_status = "Out"
            else:
                db_status = "IDLE"

            fields_to_set.append("status = :status")
            update_params["status"] = db_status

        # --- 2) active toggle from Active tab ---
        elif req.isActive is not None:
            desired_active = bool(req.isActive)
            currently_active = self.is_active_from_status(current_status)

            if desired_active == currently_active and not req.newRfidTag:
                return UserUpdateResponse(success=True, message="No changes required")

            # Active -> Inactive → Banned (admin ban, not expire)
            if not desired_active and currently_active:
                fields_to_set.append("status = :status")
                update_params["status"] = "Banned"

            # Inactive (Banned/Expired) -> Active → IDLE
            elif desired_active and not currently_active:
                fields_to_set.append("status = :status")
                update_params["status"] = "IDLE"

        # --- 3) RFID change (optional) ---
        if getattr(req, "newRfidTag", None):
            fields_to_set.append("rfid_tag = :new_rfid")
            update_params["new_rfid"] = req.newRfidTag

        if not fields_to_set:
            return UserUpdateResponse(success=True, message="No fields to update")

        # --- apply update ---
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

        # --- figure out final status after update (for logging) ---
        new_status_db = current_status
        if "status" in update_params:
            new_status_db = update_params["status"]

        # Map final DB status -> event_type + result for logs
        if new_status_db == "In":
            event_type = "ENTRY"
            result = "PASS"
        elif new_status_db == "Out":
            event_type = "EXIT"
            result = "PASS"
        elif new_status_db == "IDLE":
            # Neutral reset – still successful, just reset to idle
            event_type = "ENTRY"
            result = "PASS"
        elif new_status_db in ("Banned", "Expired"):
            event_type = "DENIED"
            result = "FAIL"
        else:
            # Fallback, should not really happen
            event_type = "ENTRY"
            result = "PASS"

        # --- build human-readable change description ---
        changes: List[str] = []

        if "status" in update_params:
            changes.append(f"status {current_status} -> {new_status_db}")

        # We still record that admin toggled active, even though it’s encoded in status
        if req.isActive is not None:
            changes.append(f"isActive set to {req.isActive}")

        if "new_rfid" in update_params:
            changes.append(f"RFID {current_rfid} -> {update_params['new_rfid']}")

        if not changes:
            log_message = "User updated via admin panel"
        else:
            log_message = "; ".join(changes)

        # --- write log entry for admin action ---
        conn.execute(
            text(
                """
                INSERT INTO logs (user_id, user_type, event_type, gate_id, booth_id, result, message, node_id)
                VALUES (:uid, :ut, :evt, :gate, :booth, :res, :msg, :node)
                """
            ),
            {
                "uid": user_id,
                "ut": user_type,
                "evt": event_type,
                "gate": ADMIN_GATE_ID,
                "booth": ADMIN_BOOTH_ID,
                "res": result,
                "msg": log_message,
                "node": ADMIN_NODE_ID,
            },
        )

        return UserUpdateResponse(success=True, message="User updated successfully")
