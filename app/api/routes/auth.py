# =======================================================================================
# app/api/routes/auth.py - Frontend Authentication Endpoints
# =======================================================================================


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection
from ...models.schemas import AdminAuthRequest, AdminAuthResponse, AdminInfo
from ...services.auth_service import AuthService
from ..dependencies import get_db_connection

router = APIRouter()
auth_service = AuthService()


@router.post("/auth/register", response_model=AdminAuthResponse)
def register_admin(
    request: AdminAuthRequest, conn: Connection = Depends(get_db_connection)
):
    # You might want to restrict this in production.
    existing = conn.execute(
        text("SELECT id FROM admins WHERE username = :u"), {"u": request.username}
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    admin_id = auth_service.create_admin(conn, request.username, request.password)

    token = auth_service.create_fake_token(admin_id, request.username)
    return AdminAuthResponse(
        token=token,
        message="Admin created successfully",
        admin=AdminInfo(id=admin_id, username=request.username),
    )


@router.post("/auth/login", response_model=AdminAuthResponse)
def login_admin(
    request: AdminAuthRequest, conn: Connection = Depends(get_db_connection)
):
    admin = auth_service.authenticate_admin(conn, request.username, request.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = auth_service.create_fake_token(admin["id"], admin["username"])
    return AdminAuthResponse(
        token=token,
        message="Login successful",
        admin=AdminInfo(id=admin["id"], username=admin["username"]),
    )
