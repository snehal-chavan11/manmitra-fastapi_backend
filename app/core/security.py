import os
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from app.core.config import settings
from app.core.db import get_db  # assuming you have a db.py in core
from bson import ObjectId
from typing import Dict, Any

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

SECRET_KEY = os.getenv("JWT_SECRET", settings.JWT_SECRET)
ALGORITHM = "HS256"


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decode JWT, fetch user from DB, and return minimal user object.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        async for db in get_db():
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            break
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Return lightweight user object
        return {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "role": user.get("role", "patient")
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_roles(*roles):
    """
    Role-based access dependency.
    Example:
        @router.get("/admin", dependencies=[Depends(require_roles("admin"))])
    """
    def role_checker(current_user=Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Access forbidden")
        return current_user

    return role_checker


class SafetyService:
    """Service for message validation and crisis detection"""
    
    def __init__(self):
        self.crisis_keywords = settings.crisis_keywords_list
    
    def validate_message(self, message: str) -> Dict[str, Any]:
        """Validate message content"""
        if not message or len(message.strip()) == 0:
            return {
                "is_valid": False,
                "reason": "Message cannot be empty",
                "sanitized_text": ""
            }
        
        # Basic sanitization
        sanitized = message.strip()
        
        # Check message length
        if len(sanitized) > settings.MAX_MESSAGE_LENGTH:
            return {
                "is_valid": False,
                "reason": f"Message too long (max {settings.MAX_MESSAGE_LENGTH} characters)",
                "sanitized_text": sanitized[:settings.MAX_MESSAGE_LENGTH]
            }
        
        return {
            "is_valid": True,
            "reason": "Message is valid",
            "sanitized_text": sanitized
        }
    
    def detect_crisis(self, message: str) -> Dict[str, Any]:
        """Detect crisis indicators in message"""
        message_lower = message.lower()
        matched_patterns = []
        
        for keyword in self.crisis_keywords:
            if keyword.lower() in message_lower:
                matched_patterns.append(keyword)
        
        if not matched_patterns:
            return {
                "is_crisis": False,
                "severity": "none",
                "matched_patterns": []
            }
        
        # Determine severity based on matched patterns
        high_severity_keywords = ["suicide", "kill myself", "end it", "don't want to live", "self harm", "hurt myself"]
        medium_severity_keywords = ["die", "death", "dead", "not worth living", "better off dead", "end my life"]
        
        severity = "low"
        if any(keyword in message_lower for keyword in high_severity_keywords):
            severity = "high"
        elif any(keyword in message_lower for keyword in medium_severity_keywords):
            severity = "medium"
        
        return {
            "is_crisis": True,
            "severity": severity,
            "matched_patterns": matched_patterns
        }

# Create safety service instance
safety_service = SafetyService()
