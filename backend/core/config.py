"""
Configuration management using Pydantic settings
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "AutoPLC Enhanced"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./autoplc.db"
    
    # API Keys
    NVIDIA_API_KEY_1: Optional[str] = None
    NVIDIA_API_KEY_2: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    
    # External services
    OPENPLC_URL: str = "http://localhost:8080"
    MATIEC_PATH: str = "/usr/local/bin/matiec"
    
    # Redis for caching (optional)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # WebSocket settings
    WS_MAX_CONNECTIONS: int = 100
    
    # Performance settings
    MAX_CONCURRENT_TASKS: int = 10
    TASK_TIMEOUT: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
