"""Sistema de cache Redis"""
import redis
import json
from typing import Optional, Any
from functools import wraps
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Gerenciador de cache Redis"""
    
    def __init__(self):
        try:
            # Configuração otimizada para 100k reqs/dia
            redis_kwargs = {
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB,
                "decode_responses": True,
                "socket_connect_timeout": 5,
                "socket_keepalive": True,
                "health_check_interval": 30,
                "retry_on_timeout": True,
                "max_connections": 100  # Pool de conexões Redis
            }
            
            if settings.REDIS_PASSWORD:
                redis_kwargs["password"] = settings.REDIS_PASSWORD
            
            
            self.redis_client = redis.Redis(**redis_kwargs)
            self.redis_client.ping()
            logger.info("Redis conectado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar Redis: {e}")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except json.JSONDecodeError:
            logger.warning(f"Erro ao decodificar cache para chave: {key}")
            return None
        except Exception as e:
            logger.warning(f"Erro ao ler cache: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Define valor no cache com TTL"""
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or settings.CACHE_TTL
            serialized = json.dumps(value, default=str)
            return self.redis_client.setex(key, ttl, serialized)
        except Exception as e:
            logger.warning(f"Erro ao escrever cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Remove chave do cache"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.warning(f"Erro ao deletar cache: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que correspondem ao padrão"""
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Erro ao deletar padrão de cache: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe no cache"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.warning(f"Erro ao verificar existência de chave: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Limpa todo o cache (usar com cuidado!)"""
        if not self.redis_client:
            return False
        
        try:
            return self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return False


# Instância global do cache
cache = CacheManager()


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator para cachear resultados de funções
    
    Uso:
        @cached(ttl=300, key_prefix="league")
        def get_league_standings(league_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gera chave única baseada nos argumentos
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Tenta obter do cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return result
            
            # Executa função e cacheia resultado
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

