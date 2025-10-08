from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
from app.api.services.ai_services import moderation_service

router = APIRouter()

class ModerationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text content to moderate")

class ModerationResponse(BaseModel):
    decision: str = Field(..., description="Moderation decision: 'allow', 'block', or 'review'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the moderation decision")
    reason: str = Field(..., description="Explanation for the moderation decision")
    flagged_content: list = Field(default=[], description="List of flagged words or phrases")
    method: str = Field(..., description="Method used for moderation: 'gemini' or 'rule_based'")

@router.post("/scan-post", response_model=ModerationResponse)
async def moderate_post(request: ModerationRequest):
    """
    Moderate forum post content for appropriateness
    
    This endpoint analyzes text content to detect toxicity, abuse, or inappropriate
    content that should not be allowed in the mental health support forum.
    """
    try:
        # Validate input
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text content cannot be empty")
        
        # Moderate content using AI service
        result = await moderation_service.moderate_post(request.text)
        
        return ModerationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in moderation endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while moderating content"
        )


