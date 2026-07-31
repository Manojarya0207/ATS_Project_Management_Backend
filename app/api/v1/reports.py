from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database.session import get_db
from app.models import User
from app.schemas.report import DashboardReport, ProjectAnalytics
from app.services.report_service import ReportService

router = APIRouter(tags=["Reports & Analytics"])


@router.get(
    "/reports/dashboard", response_model=DashboardReport, dependencies=[Depends(require_admin)]
)
def dashboard(db: Session = Depends(get_db)):
    return ReportService(db).dashboard()


@router.get("/analytics/projects/{project_id}", response_model=ProjectAnalytics)
def project_analytics(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return ReportService(db).project_analytics(user, project_id)
