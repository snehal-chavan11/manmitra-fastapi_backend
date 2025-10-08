from fastapi import APIRouter
from typing import Dict, Any
from app.api.services.ai_services import bestie_service

router = APIRouter()

@router.get("/api-status")
async def get_api_status() -> Dict[str, Any]:
    """
    Get current API status and usage statistics
    
    Returns information about:
    - API key configuration status
    - Current rate limiting status
    - Token usage statistics
    - Cache performance
    - Backoff status
    """
    try:
        status = bestie_service.gemini_service.get_api_status()
        
        return {
            "success": True,
            "status": status,
            "message": "API status retrieved successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve API status"
        }

@router.post("/validate-api-key")
async def validate_api_key() -> Dict[str, Any]:
    """
    Validate the Gemini API key by making a test request
    
    This endpoint makes a minimal API call to verify:
    - API key is valid and configured correctly
    - Quota is available for requests
    - Service is operational
    """
    try:
        validation = bestie_service.gemini_service.validate_api_key()
        
        return {
            "success": True,
            "validation": validation,
            "message": "API key validation completed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to validate API key"
        }

@router.post("/reset-rate-limits")
async def reset_rate_limits() -> Dict[str, Any]:
    """
    Reset rate limiting counters (for development/testing)
    
    WARNING: This should only be used in development environments
    """
    try:
        service = bestie_service.gemini_service
        
        # Reset rate limiting
        service.request_timestamps = []
        service.backoff_until = None
        service.consecutive_failures = 0
        
        return {
            "success": True,
            "message": "Rate limits reset successfully",
            "warning": "This should only be used in development"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to reset rate limits"
        }

@router.get("/diagnose-api-key")
async def diagnose_api_key() -> Dict[str, Any]:
    """
    Diagnose API key configuration issues
    
    Returns detailed information to help troubleshoot API key problems
    """
    try:
        from app.core.config import settings
        import os
        
        # Check environment variables
        api_key_from_env = os.getenv("GEMINI_API_KEY")
        api_key_from_settings = settings.GEMINI_API_KEY
        
        # API key format validation
        def validate_api_key_format(key: str) -> Dict[str, Any]:
            if not key or key.strip() == "":
                return {"valid": False, "reason": "API key is empty"}
            
            if key == "YOUR_NEW_API_KEY_HERE":
                return {"valid": False, "reason": "API key is still placeholder"}
            
            if not key.startswith("AIza"):
                return {"valid": False, "reason": "API key doesn't start with 'AIza' (Google format)"}
            
            if len(key) < 20:
                return {"valid": False, "reason": "API key is too short"}
            
            if " " in key or "\n" in key or "\r" in key:
                return {"valid": False, "reason": "API key contains whitespace"}
            
            return {"valid": True, "reason": "Format appears valid"}
        
        env_validation = validate_api_key_format(api_key_from_env or "")
        settings_validation = validate_api_key_format(api_key_from_settings or "")
        
        return {
            "success": True,
            "diagnosis": {
                "environment_variable": {
                    "exists": api_key_from_env is not None,
                    "first_10_chars": api_key_from_env[:10] + "..." if api_key_from_env and len(api_key_from_env) > 10 else "N/A",
                    "length": len(api_key_from_env) if api_key_from_env else 0,
                    "validation": env_validation
                },
                "settings_object": {
                    "exists": api_key_from_settings is not None,
                    "first_10_chars": api_key_from_settings[:10] + "..." if api_key_from_settings and len(api_key_from_settings) > 10 else "N/A",
                    "length": len(api_key_from_settings) if api_key_from_settings else 0,
                    "validation": settings_validation
                },
                "model_initialized": bestie_service.gemini_service.model is not None,
                "recommendations": [
                    "1. Ensure your API key starts with 'AIza' (Google format)",
                    "2. Check that there are no extra spaces or line breaks",
                    "3. Verify the key is active in Google AI Studio",
                    "4. Restart FastAPI service after updating .env file",
                    "5. Check if billing is enabled for your Google Cloud project"
                ]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to diagnose API key"
        }
