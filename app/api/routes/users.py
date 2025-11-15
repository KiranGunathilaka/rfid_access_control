# =======================================================================================
# app/api/routes/users.py - User Management Endpoints
# =======================================================================================
import io
import csv
from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
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
