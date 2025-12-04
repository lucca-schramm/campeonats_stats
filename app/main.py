"""Aplicação principal FastAPI"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import OptimizedMiddleware
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

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(OptimizedMiddleware)

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
    
    # Verifica se banco está vazio
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.league import League
        from sqlalchemy import select, func
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(func.count(League.id)))
            leagues_count = result.scalar() or 0
            if leagues_count == 0:
                logger.warning("⚠️  BANCO VAZIO DETECTADO!")
                logger.info("💡 Use POST /api/v1/collect/initial para coletar dados")
                logger.info("💡 Ou aguarde a task agendada (a cada 10 minutos)")
            else:
                logger.info(f"✅ Banco OK: {leagues_count} ligas encontradas")
    except Exception as e:
        logger.warning(f"Erro ao verificar banco: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de shutdown"""
    logger.info("Aplicação encerrando...")
    from app.core.cache import cache
    await cache.close()
    from app.core.database import close_db
    await close_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )

