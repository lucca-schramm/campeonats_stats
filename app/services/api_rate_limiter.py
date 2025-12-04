"""Rate Limiter para API FootyStats - Previne excesso de requisições"""
import time
import logging
from typing import Optional
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """
    Rate limiter robusto para API FootyStats.
    Controla requisições por segundo/minuto/hora para evitar bloqueios.
    """
    
    def __init__(
        self,
        requests_per_second: float = 2.0,  # 2 req/s = 120 req/min (seguro)
        requests_per_minute: int = 100,  # Limite por minuto
        requests_per_hour: int = 5000,  # Limite por hora
        burst_size: int = 5  # Permite burst inicial
    ):
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        
        # Histórico de requisições (timestamps)
        self.request_history = deque(maxlen=requests_per_hour)
        self.lock = Lock()
        
        # Contadores
        self.total_requests = 0
        self.blocked_requests = 0
        self.last_request_time = 0.0
        
        logger.info(f"Rate Limiter inicializado: {requests_per_second} req/s, {requests_per_minute} req/min, {requests_per_hour} req/h")
    
    def wait_if_needed(self) -> float:
        """
        Aguarda se necessário para respeitar rate limits.
        Retorna tempo de espera em segundos.
        """
        with self.lock:
            now = time.time()
            
            # Remove requisições antigas (> 1 hora)
            one_hour_ago = now - 3600
            while self.request_history and self.request_history[0] < one_hour_ago:
                self.request_history.popleft()
            
            # Verifica limite por hora
            if len(self.request_history) >= self.requests_per_hour:
                wait_time = 3600 - (now - self.request_history[0])
                if wait_time > 0:
                    logger.warning(f"⚠️  Limite por hora atingido. Aguardando {wait_time:.1f}s")
                    self.blocked_requests += 1
                    return wait_time
            
            # Verifica limite por minuto
            one_minute_ago = now - 60
            recent_requests = sum(1 for t in self.request_history if t > one_minute_ago)
            if recent_requests >= self.requests_per_minute:
                wait_time = 60 - (now - self.request_history[-self.requests_per_minute])
                if wait_time > 0:
                    logger.warning(f"⚠️  Limite por minuto atingido. Aguardando {wait_time:.1f}s")
                    self.blocked_requests += 1
                    return wait_time
            
            # Verifica limite por segundo (com burst permitido)
            time_since_last = now - self.last_request_time
            min_interval = 1.0 / self.requests_per_second
            
            # Permite burst inicial
            if self.total_requests < self.burst_size:
                wait_time = 0.0
            elif time_since_last < min_interval:
                wait_time = min_interval - time_since_last
            else:
                wait_time = 0.0
            
            # Atualiza histórico
            if wait_time > 0:
                time.sleep(wait_time)
                now = time.time()
            
            self.request_history.append(now)
            self.last_request_time = now
            self.total_requests += 1
            
            return wait_time
    
    def record_request(self, success: bool = True):
        """Registra uma requisição (para estatísticas)"""
        with self.lock:
            if success:
                # Já registrado em wait_if_needed
                pass
            else:
                # Remove da contagem se falhou antes de enviar
                if self.request_history:
                    self.request_history.pop()
                self.total_requests = max(0, self.total_requests - 1)
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do rate limiter"""
        with self.lock:
            now = time.time()
            recent_requests = sum(1 for t in self.request_history if t > now - 60)
            hourly_requests = len(self.request_history)
            
            return {
                "total_requests": self.total_requests,
                "blocked_requests": self.blocked_requests,
                "requests_last_minute": recent_requests,
                "requests_last_hour": hourly_requests,
                "requests_per_second_limit": self.requests_per_second,
                "requests_per_minute_limit": self.requests_per_minute,
                "requests_per_hour_limit": self.requests_per_hour
            }


# Instância global do rate limiter
_global_rate_limiter: Optional[APIRateLimiter] = None


def get_rate_limiter() -> APIRateLimiter:
    """Retorna instância global do rate limiter"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = APIRateLimiter()
    return _global_rate_limiter

