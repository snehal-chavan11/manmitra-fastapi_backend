from fastapi import APIRouter
from app.api.endpoints import chat, moderation, status
from app.api.endpoints import student, counselor, admin_routes
from app.api.endpoints import counselor_routes
from app.api.endpoints import analytics
api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["Bestie Chat"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["Content Moderation"])
api_router.include_router(status.router, prefix="/status", tags=["API Status"])
api_router.include_router(student.router)
api_router.include_router(counselor.router)
api_router.include_router(admin_routes.router)
api_router.include_router(counselor_routes.router)
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])