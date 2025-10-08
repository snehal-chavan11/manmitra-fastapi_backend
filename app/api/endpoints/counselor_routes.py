# routes/counselor_routes.py
from fastapi import APIRouter, Depends, HTTPException
from app.api.services.analytics import compute_counselor_analytics
from app.api.services.pdf_generator import PDFService
from app.api.models import schemas
# Placeholder auth dependency; adjust path when auth is added
def get_current_user():
    # Minimal stub for now
    class User:
        role = "counselor"
        id = "demo-counselor"
    return User()
from typing import Optional
from datetime import datetime
import base64

router = APIRouter(prefix="/counselor", tags=["counselor"])
pdf_service = PDFService()

@router.post("/analytics")
async def counselor_analytics(req: schemas.AnalyticsRequest, current_user = Depends(get_current_user)):
    # ensure user is counselor or admin
    if current_user.role not in ("counselor", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    counselor_id = req.counselor_id or current_user.id
    result = await compute_counselor_analytics(counselor_id, req.start_date, req.end_date)
    # convert binary charts to base64 for JSON transport
    charts_b64 = {}
    for k, v in result.get("charts", {}).items():
        charts_b64[k] = base64.b64encode(v).decode()
    result["charts_b64"] = charts_b64
    return result

@router.post("/analytics/pdf")
async def counselor_analytics_pdf(req: schemas.PDFRequest, current_user = Depends(get_current_user)):
    if current_user.role not in ("counselor", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    counselor_id = req.counselor_id or current_user.id
    # compute
    analytics = await compute_counselor_analytics(counselor_id, req.start_date, req.end_date)
    # Use PDFService to generate PDF (returns base64 string)
    pdf_base64 = await pdf_service.generate_counselor_pdf(counselor_id, {"analytics": analytics})
    return {"filename": f"counselor_{counselor_id}_analytics.pdf", "pdf_base64": pdf_base64}
