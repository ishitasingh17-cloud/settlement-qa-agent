from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    PORT: int = Field(default=8000, description="Server port")
    HOST: str = Field(default="127.0.0.1", description="Server host")
    ENVIRONMENT: str = Field(default="development", description="Execution environment")
    
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
