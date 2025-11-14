# =======================================================================================
# app/api/routes/dashboard
# =======================================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection
from sqlalchemy import text

from ...models.schemas import AnalyticsResponse, Summary, LogsResponse, HealthResponse
from ...services.dashboard_service import DashboardService
from ..dependencies import get_db_connection

router = APIRouter()
dashboard_service = DashboardService()


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(conn: Connection = Depends(get_db_connection)):
    summary_dict = dashboard_service.get_summary(conn)
    return AnalyticsResponse(summary=Summary(**summary_dict))


@router.get("/logs", response_model=LogsResponse)
def get_logs(conn: Connection = Depends(get_db_connection)):
    logs = dashboard_service.get_logs(conn)
    return LogsResponse(logs=logs)
