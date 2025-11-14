# =======================================================================================
# app/api/routes/users.py - User Management Endpoints
# =======================================================================================
import io
import csv
from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.engine import Connection
from ...models.schemas import CreateUserRequest, CreateUserResponse
from ...services.user_service import UserService
from ..dependencies import get_db_connection
from sqlalchemy import text
from ...models.schemas import (
    CreateUserRequest,
    CreateUserResponse,
    UserSearchResponse,
    SimpleUser,
    UserUpdateRequest,
    UserUpdateResponse,
)

router = APIRouter()
user_service = UserService()

@router.post("/users", response_model=CreateUserResponse)
def create_user(request: CreateUserRequest, conn: Connection = Depends(get_db_connection)):
    """Create a new user."""
    return user_service.create_user(conn, request)

@router.post("/users/import")
def import_users(file: UploadFile = File(...), conn: Connection = Depends(get_db_connection)):
    """Import users from CSV file."""
    return user_service.import_users_from_csv(conn, file)

@router.get("/users/{user_id}")
def get_user(user_id: int, conn: Connection = Depends(get_db_connection)):
    """Get user by ID."""
    return user_service.get_user_by_id(conn, user_id)

@router.get("/users")
def list_users(skip: int = 0, limit: int = 100, conn: Connection = Depends(get_db_connection)):
    """List users with pagination."""
    return user_service.list_users(conn, skip, limit)


# ---- search endpoint used by UserManagementModal ----

@router.get("/users/search", response_model=UserSearchResponse)
def search_users(
    query: str = Query(..., description="NIC or RFID tag"),
    conn: Connection = Depends(get_db_connection),
):
    users = user_service.search_users(conn, query)
    return UserSearchResponse(
        success=True,
        data=[SimpleUser(**u) for u in users],
    )


# ---- manual update endpoint used by UserManagementModal ----

@router.post("/user/update", response_model=UserUpdateResponse)
def manual_update_user(
    request: UserUpdateRequest, conn: Connection = Depends(get_db_connection)
):
    return user_service.update_user_manual(conn, request)
