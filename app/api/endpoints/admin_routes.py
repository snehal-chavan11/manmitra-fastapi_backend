from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime

from app.core.security import require_roles
from app.api.services.analytics_service import AnalyticsService
from app.api.services.pdf_generator import PDFService
from app.core.db import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])

analytics_service = AnalyticsService()
pdf_service = PDFService()


@router.post("/org/analytics")
async def organization_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user=Depends(require_roles("admin"))
):
    """
    Org-wide analytics: aggregates across all counselors and patients.
    Returns happiness trends, PHQ9/GAD7 summaries, cost data.
    """
    return await analytics_service.get_admin_overall_analytics(start_date, end_date)


@router.get("/therapists")
async def list_therapists(current_user=Depends(require_roles("admin"))):
    """
    List all therapists working under this organization.
    """
    return await analytics_service.get_all_therapists()


@router.get("/reports/pdf")
async def generate_org_report_pdf(current_user=Depends(require_roles("admin"))):
    """
    Generate an organization-wide PDF report (all students, counselors, and insights).
    """
    data = await analytics_service.get_admin_overall_analytics()
    pdf_bytes = await pdf_service.generate_admin_pdf(data)

    return {
        "filename": "organization_report.pdf",
        "file_base64": pdf_bytes
    }


@router.post("/publish-article")
async def publish_article(
    title: str,
    body: str,
    analytics_refs: List[str] = [],
    current_user=Depends(require_roles("admin"))
):
    """
    Admin publishes article using analytics data.
    Stored in 'articles' collection in MongoDB.
    """
    async for db in get_db():
        doc = {
            "title": title,
            "body": body,
            "analytics_refs": analytics_refs,
            "author_id": current_user["id"],
            "published_at": datetime.utcnow()
        }
        res = await db.articles.insert_one(doc)
        break

    return {"article_id": str(res.inserted_id), "status": "published"}
