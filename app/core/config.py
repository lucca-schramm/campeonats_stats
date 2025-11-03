"""Configurações da aplicação"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Configurações da aplicação"""
    
    # App
    APP_NAME: str = "Campeonatos Stats API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:80",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:80",
    ]
    
    @property
    def cors_origins_list(self) -> list:
        """Retorna lista de origens CORS"""
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        elif isinstance(self.CORS_ORIGINS, str):
            return [self.CORS_ORIGINS]
        return ["*"]
    
    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")
    DB_HOST: Optional[str] = os.getenv("DB_HOST", "localhost")
    DB_PORT: Optional[int] = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: Optional[str] = os.getenv("DB_NAME", "campeonatos_stats")
    
    @property
    def database_url(self) -> str:
        """Retorna URL completa do banco de dados"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    # Redis Cache
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "120"))
    
    # FootyStats API
    FOOTYSTATS_API_KEY: str = os.getenv("FOOTYSTATS_API_KEY", "")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.football-data-api.com")
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL",
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND",
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"
    )
    
    # Webhooks
    WEBHOOK_SECRET_KEY: Optional[str] = os.getenv("WEBHOOK_SECRET_KEY")
    WEBHOOK_TIMEOUT: int = int(os.getenv("WEBHOOK_TIMEOUT", "10"))
    WEBHOOK_MAX_RETRIES: int = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
    
    # Chatbot
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    CHATBOT_DEFAULT_TYPE: str = os.getenv("CHATBOT_DEFAULT_TYPE", "simple")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    API_KEY_HEADER: str = "X-API-Key"
    FRONTEND_API_KEY: Optional[str] = os.getenv("FRONTEND_API_KEY")
    
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    
    # Encryption (para compatibilidade)
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Permite campos extras do .env


settings = Settings()

