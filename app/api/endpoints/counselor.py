from fastapi import APIRouter, Depends
from app.core.security import require_roles
from app.api.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/counselor", tags=["Counselor Analytics"])
analytics_service = AnalyticsService()

@router.get("/students", dependencies=[Depends(require_roles("counselor"))])
async def list_students(current_user=Depends(require_roles("counselor"))):
    """
    Get list of all students this counselor is handling.
    """
    return await analytics_service.get_students_for_counselor(current_user["id"])

@router.get("/analytics", dependencies=[Depends(require_roles("counselor"))])
async def counselor_overall_analytics(current_user=Depends(require_roles("counselor"))):
    """
    Get overall analytics (happiness vs session titles).
    """
    return await analytics_service.get_counselor_analytics(current_user["id"])

@router.get("/reports/pdf", dependencies=[Depends(require_roles("counselor"))])
async def counselor_report_pdf(current_user=Depends(require_roles("counselor"))):
    """
    Generate counselor PDF report (all students + insights).
    """
    return await analytics_service.generate_counselor_pdf(current_user["id"])
