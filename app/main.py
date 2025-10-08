from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv
from app.api.router import api_router

# Load environment variables before importing settings
load_dotenv()
from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title="ManMitra AI Service",
    description="This service handles all AI-powered features for ManMitra, including the Bestie Chatbot and content moderation.",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # User frontend
        "http://localhost:3001",  # Admin frontend
        "http://localhost:3002",  # Portal
        "http://localhost:3003", 
         os.environ.get("FRONTEND_URL", ""), # Volunteer frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include API routes
app.include_router(api_router, prefix="/api")
# Health check endpoint
@app.get("/", tags=["Health Check"])
async def root():
    return {
        "message": "ManMitra AI Service is running",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "healthy",
    }


# Lightweight adapter for the frontend Chat with Bestie
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


class ChatReply(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatReply, tags=["Bestie Chat (Adapter)"])
async def chat_adapter(payload: ChatRequest):
    """
    Adapter endpoint to match the frontend's expected contract:
      Request: { message: string, user_id?: string }
      Response: { reply: string }

    Internally delegates to the existing chat pipeline.
    """
    try:
        # Defer to the existing chat endpoint logic to avoid duplication
        from app.api.endpoints.chat import ask_bestie, ChatMessage

        chat_msg = ChatMessage(message=payload.message, history=[], user_id=payload.user_id)
        result = await ask_bestie(chat_msg)
        # result has shape ChatResponse with field `response`
        return ChatReply(reply=result.response)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.ENVIRONMENT == "development" else "An error occurred"
        }
    )

if __name__ == "__main__":
    import os

    uvicorn.run(
        "app.main:app",  # note the path
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),  # use Render's port if available
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )

