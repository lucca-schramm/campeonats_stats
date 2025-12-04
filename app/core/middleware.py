"""Middleware otimizado de performance e segurança"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from time import perf_counter
import logging

logger = logging.getLogger(__name__)


class OptimizedMiddleware(BaseHTTPMiddleware):
    """Middleware combinado para performance e segurança"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = perf_counter()
        
        # Processa requisição
        response = await call_next(request)
        
        # Calcula tempo de processamento
        process_time = perf_counter() - start_time
        
        # Headers de performance
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "unknown")
        
        # Headers de segurança
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Log de requisições lentas (> 1s)
        if process_time > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {process_time:.4f}s"
            )
        
        return response

