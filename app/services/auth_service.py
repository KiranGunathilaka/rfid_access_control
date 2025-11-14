# =======================================================================================
# app/services/auth_service.py - Authentication for the frontend
# =======================================================================================

from typing import Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Connection
from passlib.context import CryptContext

from ..config import config

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class AuthService:
    """Handles admin authentication (username/password)."""

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_admin(self, conn: Connection, username: str, password: str) -> int:
        result = conn.execute(
            text(
                """
                INSERT INTO admins (username, password_hash)
                VALUES (:username, :password_hash)
                """
            ),
            {"username": username, "password_hash": self.hash_password(password)},
        )
        return result.lastrowid

    def authenticate_admin(
        self, conn: Connection, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        row = conn.execute(
            text(
                """
                SELECT id, username, password_hash
                FROM admins
                WHERE username = :username
                """
            ),
            {"username": username},
        ).mappings().first()

        if not row:
            return None

        if not self.verify_password(password, row["password_hash"]):
            return None

        return {"id": row["id"], "username": row["username"]}

    def create_fake_token(self, admin_id: int, username: str) -> str:
        """
        For now: simple opaque token. Frontend only checks that *some* token exists.
        Later you can swap this to real JWT if you like.
        """
        return f"admin-{admin_id}-{username}"
