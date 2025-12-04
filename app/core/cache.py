"""Sistema de cache Redis async"""
import json
from typing import Optional, Any, Callable
from functools import wraps
import logging
from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Gerenciador de cache Redis async"""
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
    
    async def _get_client(self) -> Optional[Redis]:
        """Obtém cliente Redis (lazy initialization)"""
        if self._client:
            return self._client
        
        try:
            self._pool = ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
                max_connections=50,
            )
            self._client = Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info("Redis conectado com sucesso")
            return self._client
        except Exception as e:
            logger.error(f"Erro ao conectar Redis: {e}")
            return None
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        client = await self._get_client()
        if not client:
            return None
        
        try:
            value = await client.get(key)
            return json.loads(value) if value else None
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Erro ao ler cache {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Define valor no cache com TTL"""
        client = await self._get_client()
        if not client:
            return False
        
        try:
            ttl = ttl or settings.CACHE_TTL
            serialized = json.dumps(value, default=str)
            return await client.setex(key, ttl, serialized)
        except Exception as e:
            logger.warning(f"Erro ao escrever cache {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Remove chave do cache"""
        client = await self._get_client()
        if not client:
            return False
        
        try:
            return bool(await client.delete(key))
        except Exception as e:
            logger.warning(f"Erro ao deletar cache {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que correspondem ao padrão"""
        client = await self._get_client()
        if not client:
            return 0
        
        try:
            keys = [key async for key in client.scan_iter(match=pattern)]
            return await client.delete(*keys) if keys else 0
        except Exception as e:
            logger.warning(f"Erro ao deletar padrão {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Verifica se chave existe no cache"""
        client = await self._get_client()
        if not client:
            return False
        
        try:
            return bool(await client.exists(key))
        except Exception as e:
            logger.warning(f"Erro ao verificar cache {key}: {e}")
            return False
    
    async def close(self):
        """Fecha conexões Redis"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()


# Instância global do cache
cache = CacheManager()


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator async para cachear resultados de funções
    
    Uso:
        @cached(ttl=300, key_prefix="league")
        async def get_league_standings(league_id: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Gera chave única baseada nos argumentos
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Tenta obter do cache
            result = await cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return result
            
            # Executa função e cacheia resultado
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

