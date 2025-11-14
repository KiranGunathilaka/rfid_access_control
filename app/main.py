# =======================================================================================
# app/main.py - FastAPI Application Entry Point
# =======================================================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import config
from .api.routes.scan import router as scan_router
from .api.routes.users import router as users_router
from .api.routes.sync import router as sync_router
from .api.routes.auth import router as auth_router
from .api.routes.dashboard import router as dashboard_router  # we'll add this below
from .database import db_manager
from .models.schemas import HealthResponse
from .workers.serial_worker import start_serial_worker


def create_app() -> FastAPI:
    app = FastAPI(
        title="RFID Access Control API",
        version="2.0.0",
        description="Modular RFID Access Control System for Multi-Gate Architecture",
        debug=config.API_DEBUG,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(scan_router, prefix="/api", tags=["scan"])
    app.include_router(users_router, prefix="/api", tags=["users"])
    app.include_router(sync_router, prefix="/api", tags=["sync"])
    app.include_router(auth_router, prefix="/api", tags=["auth"])
    app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def api_health():
        try:
            db_manager.fetch_one("SELECT 1")
            return HealthResponse(status="ok", dataAvailable=True, message=None)
        except Exception as e:
            return HealthResponse(
                status="error", dataAvailable=False, message=str(e)
            )

    # to keep old /health for backwards compatibility
    @app.get("/health")
    def legacy_health():
        return {"status": "ok", "dataAvailable": True}

    @app.on_event("startup")
    async def startup_event():
        start_serial_worker()
        if config.API_DEBUG:
            print("RFID Access Control API started successfully")

    return app


app = create_app()
