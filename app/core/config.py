import os
from typing import List, Any
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ManMitra AI Service"
    
    # CORS Configuration
    CORS_ORIGINS: Any = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.strip() == '':
                return ["http://localhost:3000", "http://localhost:5173"]
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash-exp", env="GEMINI_MODEL")
    
    # AI Service Configuration
    MAX_CONTEXT_MESSAGES: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "10"))
    SUMMARIZE_THRESHOLD: int = int(os.getenv("SUMMARIZE_THRESHOLD", "20"))
    
    # Crisis Detection Configuration
    CRISIS_KEYWORDS: str = Field(
        default="suicide,kill myself,end it,don't want to live,self harm,hurt myself,die,death,dead,not worth living,better off dead,end my life",
        env="CRISIS_KEYWORDS"
    )
    
    @property
    def crisis_keywords_list(self) -> List[str]:
        """Get crisis keywords as a list"""
        if not self.CRISIS_KEYWORDS or self.CRISIS_KEYWORDS.strip() == "":
            return [
                "suicide", "kill myself", "end it", "don't want to live",
                "self harm", "hurt myself", "die", "death", "dead",
                "not worth living", "better off dead", "end my life"
            ]
        return [keyword.strip() for keyword in self.CRISIS_KEYWORDS.split(',')]
    
    # Safety Configuration
    SAFETY_TEMPERATURE: float = Field(default=0.2, env="SAFETY_TEMPERATURE")
    CHAT_TEMPERATURE: float = Field(default=0.7, env="CHAT_TEMPERATURE")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    MONGO_URI: str = Field(default="mongodb://localhost:27017", env="MONGO_URI")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "chatbot_db")
    
    # JWT Secret
    JWT_SECRET: str = Field(default="SuperSecretKey123", env="JWT_SECRET")
    
    # Message validation
    MAX_MESSAGE_LENGTH: int = Field(default=2000, env="MAX_MESSAGE_LENGTH")
    
    # Crisis detection keywords
    CRISIS_KEYWORDS: str = Field(
        default="suicide,kill myself,end it,don't want to live,self harm,hurt myself,die,death,dead,not worth living,better off dead,end my life",
        env="CRISIS_KEYWORDS"
    )
    
    @property
    def crisis_keywords_list(self) -> list:
        """Convert crisis keywords string to list"""
        return [keyword.strip() for keyword in self.CRISIS_KEYWORDS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Create settings instance
settings = Settings()
