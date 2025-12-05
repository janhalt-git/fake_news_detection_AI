from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"
    gemini_api_key: Optional[str] = None
    google_factcheck_api_key: Optional[str] = None
    log_llm_calls: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()