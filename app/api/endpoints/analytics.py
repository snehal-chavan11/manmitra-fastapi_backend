from fastapi import APIRouter, HTTPException, Response
from app.api.services.analytics_service import AnalyticsService
from app.api.services.pdf_generator import PDFService
import base64

router = APIRouter()

@router.get("/student/{student_id}")
async def get_student_analytics(student_id: str):
    svc = AnalyticsService()
    data = await svc.get_student_happiness(student_id)
    if isinstance(data, dict) and "error" in data:
        # Graceful fallback when DB not ready or no data
        return {
            "student_id": student_id,
            "happiness_trend": [],
            "average_happiness": 0,
            "trend": "stable",
            "fallback": True,
            "detail": data,
        }
    return data

@router.get("/pdf/{student_id}")
async def get_student_pdf(student_id: str):
    svc = AnalyticsService()
    pdfs = PDFService()

    analytics = await svc.get_student_happiness(student_id)
    if isinstance(analytics, dict) and "error" in analytics:
        # Return a minimal placeholder PDF so UI doesn't break
        placeholder = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
        return Response(content=placeholder, media_type="application/pdf")

    # generate base64 PDF then return as binary bytes
    pdf_b64 = await pdfs.generate_student_pdf(student_id, {"happiness_data": analytics})
    try:
        pdf_bytes = base64.b64decode(pdf_b64)
    except Exception as exc:
        # Fallback to placeholder PDF on decode error
        placeholder = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
        return Response(content=placeholder, media_type="application/pdf")

    return Response(content=pdf_bytes, media_type="application/pdf")
