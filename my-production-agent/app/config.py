from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    PORT: int = 8000
    LOG_LEVEL: str = "info"
    
    # Security
    AGENT_API_KEY: str = "secret"
    
    # State & Throttling
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 10
    MONTHLY_BUDGET_USD: float = 10.0
    
    # Load from .env if present
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
