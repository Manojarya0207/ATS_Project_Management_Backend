"""Reports & analytics API routes (v1 paths preserved: /reports, /analytics)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.dependencies import DbDep
from app.core.permissions import require_admin
from app.modules.analytics.schemas import DashboardReport, ProjectAnalytics
from app.modules.analytics.service import AnalyticsService
from app.modules.projects.permissions import require_project_view
from app.shared.responses import ApiResponse, ok

router = APIRouter(tags=["Reports & Analytics"])


def get_analytics_service(db: DbDep) -> AnalyticsService:
    return AnalyticsService(db)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get(
    "/reports/dashboard",
    response_model=ApiResponse[DashboardReport],
    dependencies=[Depends(require_admin)],
)
async def dashboard(service: AnalyticsServiceDep) -> dict[str, Any]:
    return ok(await service.dashboard())


@router.get(
    "/analytics/projects/{project_id}",
    response_model=ApiResponse[ProjectAnalytics],
    dependencies=[Depends(require_project_view)],
)
async def project_analytics(project_id: uuid.UUID, service: AnalyticsServiceDep) -> dict[str, Any]:
    return ok(await service.project_analytics(project_id))
