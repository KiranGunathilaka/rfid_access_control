# =======================================================================================
# app/main.py - FastAPI Application Entry Point
# =======================================================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import config
from .api.routes.scan import router as scan_router
from .api.routes.users import router as users_router
from .api.routes.sync import router as sync_router
from .workers.serial_worker import start_serial_worker

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="RFID Access Control API",
        version="2.0.0",
        description="Modular RFID Access Control System for Multi-Gate Architecture",
        debug=config.API_DEBUG
    )
    
    # Add CORS middleware for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(scan_router, prefix="/api", tags=["scan"])
    app.include_router(users_router, prefix="/api", tags=["users"])
    app.include_router(sync_router, prefix="/api", tags=["sync"])
    
    # Health check endpoint
    @app.get("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "2.0.0"}
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        start_serial_worker()
        if config.API_DEBUG:
            print("RFID Access Control API started successfully")
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        #debug=config.API_DEBUG,
        reload=config.API_DEBUG
    )