from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.api.services.ai_services import bestie_service, moderation_service

router = APIRouter()


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User's message to Bestie")
    history: List[Dict[str, Any]] = Field(default=[], description="Previous conversation history")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    topic: Optional[str] = Field(None, description="Conversation topic")
    locale: Optional[str] = Field(None, description="User's preferred language")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Bestie's response message")
    agent: Optional[str] = Field(None, description="AI agent that generated the response")
    crisis_detected: bool = Field(default=False, description="Whether crisis was detected")
    crisis_level: Optional[str] = Field(None, description="Crisis severity level")
    type: str = Field(default="chat", description="Response type")
    metadata: Dict[str, Any] = Field(default={}, description="Additional response metadata")

@router.post("/ask", response_model=ChatResponse)
async def ask_bestie(chat_message: ChatMessage):
    """
    Send a message to Bestie and get a response
    
    This endpoint processes user messages through Bestie's multi-agent system,
    including crisis detection, tone adaptation, and empathetic responses.
    """
    try:
        # Validate input
        if not chat_message.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Try to use AI service first
        try:
            result = await bestie_service.process_message(
                message=chat_message.message,
                history=chat_message.history,
                user_id=chat_message.user_id,
                topic=chat_message.topic
            )
            
            # Use AI response if successful
            response_data = {
                "response": result.get("message", result.get("response", "I'm here to listen and support you.")),
                "agent": result.get("agent", "listener"),
                "crisis_detected": result.get("crisis_detected", False),
                "crisis_level": result.get("crisis_level"),
                "type": result.get("type", "chat"),
                "metadata": result.get("metadata", {
                    "user_id": chat_message.user_id,
                    "topic": chat_message.topic
                })
            }
        except Exception as ai_error:
            print(f"AI service error (using fallback): {ai_error}")
            # Fallback response if AI service fails
            response_data = {
                "response": f"I hear you saying: '{chat_message.message}'. I'm here to listen and support you. How are you feeling right now?",
                "agent": "listener",
                "crisis_detected": False,
                "crisis_level": None,
                "type": "chat",
                "metadata": {
                    "user_id": chat_message.user_id,
                    "topic": chat_message.topic,
                    "fallback": True
                }
            }
        
        return ChatResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing your message"
        )


@router.post("/summarize")
async def summarize_chat(
    messages: List[Dict[str, Any]] = Body(...),
    session_id: Optional[str] = Body(None),
    topic: Optional[str] = Body(None)
):
    """
    Generate a summary of chat conversation
    
    This endpoint creates a privacy-preserving summary of the conversation
    for storage and potential sharing with counselors (with consent).
    """
    try:
        if not messages:
            raise HTTPException(status_code=400, detail="Messages cannot be empty")
        
        # Generate summary using Moderation service
        summary = await moderation_service.generate_summary(
            messages=messages,
            session_id=session_id,
            topic=topic
        )
        
        return {
            "summary": summary,
            "session_id": session_id,
            "message_count": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in summarize endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate chat summary"
        )

