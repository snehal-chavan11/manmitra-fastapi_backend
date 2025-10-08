from fastapi import APIRouter, Depends
from app.core.security import require_roles
from app.api.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/student", tags=["Student Analytics"])
analytics_service = AnalyticsService()

@router.get("/happiness-trend", dependencies=[Depends(require_roles("patient"))])
async def get_student_happiness(current_user=Depends(require_roles("patient"))):
    """
    Returns happiness trend graph for the logged-in student.
    """
    return await analytics_service.get_student_happiness(current_user["id"])

@router.get("/reports/pdf", dependencies=[Depends(require_roles("patient"))])
async def download_student_report(current_user=Depends(require_roles("patient"))):
    """
    Generate PDF report for this student (PHQ9, GAD7, session summary).
    """
    return await analytics_service.generate_student_pdf(current_user["id"])
