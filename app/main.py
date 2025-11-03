"""Aplicação principal FastAPI"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import PerformanceMiddleware, SecurityHeadersMiddleware
from app.api.v1.api import api_router
import logging

# Configura logging
setup_logging()
logger = logging.getLogger(__name__)

# Rate Limiter - Configurado para 100k reqs/dia = ~1157 reqs/hora = ~19 reqs/min por IP
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour", "100/minute"]  # Generoso mas protege contra abuso
)

# Cria aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST para dados de futebol com webhooks e chatbot - Otimizada para 100k reqs/dia",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Estado do limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middlewares (ordem importa!)
# 1. Performance (primeiro para medir tudo)
app.add_middleware(PerformanceMiddleware)

# 2. Segurança
app.add_middleware(SecurityHeadersMiddleware)

# 3. Compressão GZip (reduz tamanho de respostas em ~70%)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 4. CORS (último)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,  # Cache CORS por 1 hora
)

# Inclui routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "leagues": f"{settings.API_V1_PREFIX}/leagues",
            "chatbot": f"{settings.API_V1_PREFIX}/chatbot",
            "webhooks": f"{settings.API_V1_PREFIX}/webhooks"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


@app.on_event("startup")
async def startup_event():
    """Evento de startup"""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} iniciando...")
    logger.info(f"Debug mode: {settings.DEBUG}")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de shutdown"""
    logger.info("Aplicação encerrando...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

