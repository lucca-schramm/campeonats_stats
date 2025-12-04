"""Configurações da aplicação"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import cached_property


class Settings(BaseSettings):
    """Configurações da aplicação"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )
    
    # App
    APP_NAME: str = "Campeonatos Stats API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development ou production
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:80,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:80"
    )
    
    @cached_property
    def is_production(self) -> bool:
        """Verifica se está em modo produção"""
        return self.ENVIRONMENT.lower() == "production"
    
    @cached_property
    def is_development(self) -> bool:
        """Verifica se está em modo desenvolvimento"""
        return self.ENVIRONMENT.lower() == "development"
    
    @cached_property
    def cors_origins_list(self) -> list[str]:
        """Retorna lista de origens CORS"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # Database
    DATABASE_URL: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "campeonatos_stats"
    
    @cached_property
    def database_url(self) -> str:
        """Retorna URL completa do banco de dados"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    # Redis Cache
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL: int = 120
    
    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "admin"
    RABBITMQ_PASSWORD: str = "admin"
    RABBITMQ_VHOST: str = "/"
    
    # FootyStats API
    FOOTYSTATS_API_KEY: str = ""
    API_BASE_URL: str = "https://api.football-data-api.com"
    
    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    @cached_property
    def celery_broker_url(self) -> str:
        """URL do broker Celery (RabbitMQ)"""
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        # Usa RabbitMQ como broker padrão
        vhost = self.RABBITMQ_VHOST.strip()
        if not vhost or vhost == '/':
            vhost = '/'
        elif not vhost.startswith('/'):
            vhost = '/' + vhost
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{vhost}"
    
    @cached_property
    def celery_result_backend(self) -> str:
        """URL do backend de resultados Celery (Redis)"""
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        # Redis continua como result backend
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    # Webhooks
    WEBHOOK_SECRET_KEY: Optional[str] = None
    WEBHOOK_TIMEOUT: int = 10
    WEBHOOK_MAX_RETRIES: int = 3
    
    # Chatbot
    OPENAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    CHATBOT_DEFAULT_TYPE: str = "rag"  # RAG por padrão para interação com banco de dados
    CHATBOT_MODEL: str = "deepseek-chat"  # Modelo DeepSeek a usar
    CHATBOT_TEMPERATURE: float = 0.7  # Temperatura para respostas mais naturais
    # Otimizações de tokens
    CHATBOT_MAX_CONTEXT_ITEMS: int = 10  # Máximo de itens no contexto (economia de tokens)
    CHATBOT_MAX_HISTORY_MESSAGES: int = 4  # Máximo de mensagens no histórico (2 interações)
    CHATBOT_MAX_CONTEXT_LENGTH: int = 2000  # Máximo de caracteres no contexto
    CHATBOT_SKIP_INTENT_ANALYSIS_IF_SIMPLE: bool = True  # Pula análise LLM se for greeting/help simples
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    FRONTEND_API_KEY: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Encryption
    ENCRYPTION_KEY: Optional[str] = None


settings = Settings()

