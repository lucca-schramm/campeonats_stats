# 📊 Plano de Melhorias e Otimizações - Campeonatos Stats

## 📋 Análise do Projeto Atual

### Arquitetura Atual
- **Banco de Dados**: SQLite (limitação para produção)
- **Processamento**: Sequencial com ThreadPoolExecutor básico
- **Armazenamento**: Arquivos JSON estáticos
- **APIs**: Nenhuma API REST implementada
- **Comunicação**: Apenas coleta de dados, sem exposição de serviços

### Pontos Fortes
✅ Coleta automatizada de dados
✅ Estrutura de dados bem definida
✅ Tratamento de erros básico
✅ Suporte a múltiplas ligas
✅ Exportação em JSON

### Limitações Identificadas
❌ SQLite não escalável para produção
❌ Sem cache de dados frequentes
❌ Processamento síncrono lento
❌ Sem API REST para acesso aos dados
❌ Sem sistema de webhooks
❌ Sem interface de chatbot
❌ Sem monitoramento e métricas

---

## 🚀 Otimizações para Larga Escala

### 1. Migração de Banco de Dados

#### 1.1 De SQLite para PostgreSQL

**Problema**: SQLite não suporta concorrência alta e tem limites de tamanho.

**Solução**: Migrar para PostgreSQL com connection pooling.

**Implementação**:

```python
# requirements.txt - Adicionar
psycopg2-binary>=2.9.9
sqlalchemy>=2.0.23
alembic>=1.12.1  # Para migrations

# config/database.py (NOVO ARQUIVO)
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', 5432)}/{os.getenv('DB_NAME')}"
)

# Connection pool otimizado
engine = create_engine(
    DATABASE_URL,
    poolclass=pool.QueuePool,
    pool_size=20,  # Número de conexões no pool
    max_overflow=40,  # Máximo de conexões extras
    pool_pre_ping=True,  # Verifica conexões antes de usar
    pool_recycle=3600,  # Recicla conexões após 1 hora
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Migrations com Alembic**:

```bash
# Inicializar Alembic
alembic init alembic

# Criar migration inicial
alembic revision --autogenerate -m "Migrate from SQLite to PostgreSQL"

# Aplicar migration
alembic upgrade head
```

**Indices necessários para performance**:

```sql
-- Adicionar índices críticos
CREATE INDEX idx_fixtures_league_season ON fixtures(league_id, season_id);
CREATE INDEX idx_fixtures_status_date ON fixtures(status, date_unix);
CREATE INDEX idx_fixtures_teams ON fixtures(home_team_id, away_team_id);
CREATE INDEX idx_teams_league_season ON teams(league_id, season_id);
CREATE INDEX idx_players_team_season ON players(team_id, season_id);
CREATE INDEX idx_team_stats_league_season ON team_statistics(league_id, season_id);

-- Índices compostos para consultas frequentes
CREATE INDEX idx_fixtures_complete_stats ON fixtures(league_id, status, home_goal_count, away_goal_count)
WHERE status = 'complete';
```

---

### 2. Sistema de Cache (Redis)

**Objetivo**: Reduzir carga no banco de dados para consultas frequentes.

**Implementação**:

```python
# requirements.txt - Adicionar
redis>=5.0.1
hiredis>=2.2.3  # Parser mais rápido

# config/cache.py (NOVO ARQUIVO)
import redis
import json
from typing import Optional, Any
import os
from functools import wraps

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        try:
            value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"Erro ao ler cache: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Define valor no cache com TTL"""
        try:
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.warning(f"Erro ao escrever cache: {e}")
    
    def delete(self, key: str):
        """Remove chave do cache"""
        try:
            self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Erro ao deletar cache: {e}")
    
    def delete_pattern(self, pattern: str):
        """Remove todas as chaves que correspondem ao padrão"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Erro ao deletar padrão de cache: {e}")

cache = CacheManager()

def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator para cachear resultados de funções"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gera chave única baseada nos argumentos
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Tenta obter do cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Executa função e cacheia resultado
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

**Uso no código**:

```python
from config.cache import cached, cache

@cached(ttl=300, key_prefix="league")
def get_league_standings(league_id: int):
    """Tabela de classificação cacheada por 5 minutos"""
    # ... código existente ...
    return standings

# Invalidar cache quando dados são atualizados
def export_league_data_to_json(self, league_id: int, ...):
    # ... exportar dados ...
    cache.delete_pattern(f"league:*{league_id}*")
```

---

### 3. Sistema de Filas para Processamento Assíncrono

**Problema**: Processamento síncrono bloqueia o sistema.

**Solução**: Usar Celery ou RQ para processamento assíncrono.

**Opção 1: Celery (Recomendado para produção)**:

```python
# requirements.txt - Adicionar
celery>=5.3.4
celery[redis]>=5.3.4

# tasks/celery_app.py (NOVO ARQUIVO)
from celery import Celery
import os

celery_app = Celery(
    'campeonatos_stats',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora máximo por tarefa
    worker_max_tasks_per_child=50,  # Previne memory leaks
)

# tasks/data_collection.py (NOVO ARQUIVO)
from tasks.celery_app import celery_app
from main import FootballDataCollector
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def collect_league_data_task(self, league_config_dict: dict):
    """Tarefa assíncrona para coletar dados de uma liga"""
    try:
        from dataclasses import asdict
        from main import LeagueConfig
        
        league_config = LeagueConfig(**league_config_dict)
        collector = FootballDataCollector()
        collector.collect_league_data(league_config)
        
        return {"status": "success", "league_id": league_config.id}
    except Exception as e:
        logger.error(f"Erro ao coletar dados da liga: {e}")
        # Retry com backoff exponencial
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@celery_app.task
def export_league_json_task(league_id: int):
    """Tarefa assíncrona para exportar JSON"""
    try:
        collector = FootballDataCollector()
        result = collector.export_league_data_to_json(league_id)
        return {"status": "success", "league_id": league_id}
    except Exception as e:
        logger.error(f"Erro ao exportar JSON: {e}")
        raise
```

**Executar workers**:

```bash
# Terminal 1: Worker Celery
celery -A tasks.celery_app worker --loglevel=info --concurrency=4

# Terminal 2: Beat scheduler (opcional, para tarefas periódicas)
celery -A tasks.celery_app beat --loglevel=info
```

**Opção 2: RQ (Mais simples)**:

```python
# requirements.txt - Adicionar (alternativa)
rq>=1.15.1

# tasks/rq_tasks.py (NOVO ARQUIVO)
from rq import Queue
from redis import Redis
from main import FootballDataCollector, LeagueConfig

redis_conn = Redis(host='localhost', port=6379, db=0)
task_queue = Queue('default', connection=redis_conn)

def collect_league_data_job(league_config_dict: dict):
    """Job RQ para coletar dados de liga"""
    league_config = LeagueConfig(**league_config_dict)
    collector = FootballDataCollector()
    collector.collect_league_data(league_config)
    return {"status": "success"}

# Enfileirar tarefa
def collect_all_data_async():
    collector = FootballDataCollector()
    collector.load_leagues_from_api()
    
    for league in collector.leagues:
        task_queue.enqueue(
            collect_league_data_job,
            league.__dict__,
            job_timeout='1h'
        )
```

**Executar worker RQ**:

```bash
rq worker --url redis://localhost:6379/0
```

---

### 4. API REST com FastAPI

**Objetivo**: Expor dados via endpoints RESTful.

**Implementação**:

```python
# requirements.txt - Adicionar
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
python-multipart>=0.0.6

# api/main.py (NOVO ARQUIVO)
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from config.database import get_db
from config.cache import cache
from queries import FootballAnalyzer

app = FastAPI(
    title="Campeonatos Stats API",
    description="API REST para dados de futebol",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    return {
        "message": "Campeonatos Stats API",
        "version": "1.0.0",
        "endpoints": {
            "leagues": "/api/v1/leagues",
            "league_standings": "/api/v1/leagues/{league_id}/standings",
            "league_teams": "/api/v1/leagues/{league_id}/teams",
            "league_fixtures": "/api/v1/leagues/{league_id}/fixtures",
            "league_top_scorers": "/api/v1/leagues/{league_id}/top-scorers"
        }
    }

@app.get("/api/v1/leagues")
async def get_leagues(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Lista todas as ligas disponíveis"""
    cache_key = f"leagues:list:{skip}:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    analyzer = FootballAnalyzer()
    # Buscar ligas do banco
    # ... implementação ...
    
    result = {"leagues": leagues, "total": total}
    cache.set(cache_key, result, ttl=3600)
    return result

@app.get("/api/v1/leagues/{league_id}/standings")
async def get_league_standings(
    league_id: int,
    db: Session = Depends(get_db),
    season_id: Optional[int] = None
):
    """Obtém tabela de classificação de uma liga"""
    cache_key = f"league:{league_id}:standings:{season_id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    analyzer = FootballAnalyzer()
    standings = analyzer.get_league_standings(league_id)
    
    result = standings.to_dict('records')
    cache.set(cache_key, result, ttl=300)  # 5 minutos
    return {"league_id": league_id, "standings": result}

@app.get("/api/v1/leagues/{league_id}/fixtures")
async def get_league_fixtures(
    league_id: int,
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Obtém partidas de uma liga"""
    # Implementar com paginação
    pass

@app.get("/api/v1/leagues/{league_id}/top-scorers")
async def get_top_scorers(league_id: int, limit: int = Query(20, ge=1, le=100)):
    """Obtém artilharia da liga"""
    cache_key = f"league:{league_id}:top_scorers:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    analyzer = FootballAnalyzer()
    from main import FootballDataCollector
    collector = FootballDataCollector()
    scorers = collector.get_league_top_scorers_from_db(league_id)
    
    result = scorers[:limit]
    cache.set(cache_key, result, ttl=3600)
    return {"league_id": league_id, "top_scorers": result}

# Executar API
# uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Rate Limiting**:

```python
# requirements.txt - Adicionar
slowapi>=0.1.9

# api/middleware.py (NOVO ARQUIVO)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/leagues/{league_id}/standings")
@limiter.limit("100/minute")  # 100 requisições por minuto
async def get_league_standings(...):
    ...
```

---

## 🔔 Sistema de Webhooks

### Arquitetura de Webhooks

**Objetivo**: Notificar automaticamente clientes quando dados de liga são atualizados.

### 1. Estrutura de Banco de Dados para Webhooks

```sql
-- Nova tabela para armazenar webhooks registrados
CREATE TABLE webhook_subscriptions (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    league_id INTEGER,
    events TEXT[],  -- Array de eventos: ['standings_updated', 'fixture_updated', etc.]
    secret TEXT,  -- Para validação de webhook
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

CREATE TABLE webhook_logs (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER,
    event_type TEXT,
    payload JSONB,
    response_code INTEGER,
    response_body TEXT,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subscription_id) REFERENCES webhook_subscriptions(id)
);
```

### 2. Implementação do Sistema de Webhooks

```python
# webhooks/manager.py (NOVO ARQUIVO)
import requests
import json
import hmac
import hashlib
import time
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from config.database import SessionLocal
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookManager:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CampeonatosStats-Webhook/1.0'
        })
    
    def generate_signature(self, payload: str, secret: str) -> str:
        """Gera assinatura HMAC-SHA256 para validação"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def register_webhook(
        self,
        url: str,
        league_id: Optional[int],
        events: List[str],
        secret: Optional[str] = None
    ) -> int:
        """Registra um novo webhook"""
        db = SessionLocal()
        try:
            from api.models import WebhookSubscription
            
            subscription = WebhookSubscription(
                url=url,
                league_id=league_id,
                events=events,
                secret=secret or self._generate_secret(),
                active=True
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            logger.info(f"Webhook registrado: {subscription.id} -> {url}")
            return subscription.id
        finally:
            db.close()
    
    def trigger_webhook(
        self,
        event_type: str,
        league_id: int,
        data: Dict
    ):
        """Dispara webhook para todos os subscribers do evento"""
        db = SessionLocal()
        try:
            from api.models import WebhookSubscription, WebhookLog
            
            # Busca subscriptions ativas que escutam este evento
            subscriptions = db.query(WebhookSubscription).filter(
                WebhookSubscription.active == True,
                WebhookSubscription.league_id == league_id,
                WebhookSubscription.events.contains([event_type])
            ).all()
            
            for subscription in subscriptions:
                try:
                    payload = {
                        "event": event_type,
                        "league_id": league_id,
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    headers = {
                        'X-Webhook-Signature': self.generate_signature(
                            json.dumps(payload),
                            subscription.secret
                        ),
                        'X-Webhook-Event': event_type,
                        'X-Webhook-Timestamp': str(int(time.time()))
                    }
                    
                    response = self.session.post(
                        subscription.url,
                        json=payload,
                        headers=headers,
                        timeout=10
                    )
                    
                    # Log do webhook
                    log = WebhookLog(
                        subscription_id=subscription.id,
                        event_type=event_type,
                        payload=payload,
                        response_code=response.status_code,
                        response_body=response.text[:1000]  # Limita tamanho
                    )
                    db.add(log)
                    
                    # Atualiza último triggered
                    subscription.last_triggered_at = datetime.utcnow()
                    
                    if response.status_code >= 400:
                        subscription.failure_count += 1
                        if subscription.failure_count >= 5:
                            subscription.active = False
                            logger.warning(
                                f"Webhook {subscription.id} desativado após 5 falhas"
                            )
                    else:
                        subscription.failure_count = 0
                    
                    db.commit()
                    logger.info(
                        f"Webhook {subscription.id} disparado: "
                        f"{event_type} -> {subscription.url} ({response.status_code})"
                    )
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Erro ao disparar webhook {subscription.id}: {e}")
                    subscription.failure_count += 1
                    db.commit()
                except Exception as e:
                    logger.error(f"Erro inesperado no webhook {subscription.id}: {e}")
                    db.rollback()
                    
        finally:
            db.close()
    
    def _generate_secret(self) -> str:
        """Gera secret aleatório"""
        import secrets
        return secrets.token_urlsafe(32)
```

### 3. Integração com Coleta de Dados

```python
# Modificar main.py para disparar webhooks

# No método collect_league_data, após atualizar dados:
from webhooks.manager import WebhookManager

def collect_league_data(self, league_config: LeagueConfig):
    # ... código existente de coleta ...
    
    # Disparar webhook após atualização
    webhook_manager = WebhookManager()
    
    # Webhook: standings atualizados
    standings_data = self._get_standings_data(league_config.id)
    webhook_manager.trigger_webhook(
        event_type="standings_updated",
        league_id=league_config.id,
        data=standings_data
    )
    
    # Webhook: fixtures atualizados
    fixtures_data = self._get_recent_fixtures(league_config.id)
    webhook_manager.trigger_webhook(
        event_type="fixtures_updated",
        league_id=league_config.id,
        data=fixtures_data
    )
```

### 4. Endpoints de API para Gerenciar Webhooks

```python
# api/webhooks.py (NOVO ARQUIVO)
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from webhooks.manager import WebhookManager

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

class WebhookSubscriptionRequest(BaseModel):
    url: HttpUrl
    league_id: Optional[int] = None
    events: List[str]  # ['standings_updated', 'fixture_updated', 'top_scorer_updated']

class WebhookSubscriptionResponse(BaseModel):
    id: int
    url: str
    league_id: Optional[int]
    events: List[str]
    active: bool
    created_at: str

@router.post("/", response_model=WebhookSubscriptionResponse)
async def create_webhook(
    subscription: WebhookSubscriptionRequest,
    db: Session = Depends(get_db)
):
    """Registra um novo webhook"""
    webhook_manager = WebhookManager()
    
    # Valida eventos permitidos
    allowed_events = ['standings_updated', 'fixture_updated', 'top_scorer_updated']
    if not all(e in allowed_events for e in subscription.events):
        raise HTTPException(400, "Eventos inválidos")
    
    subscription_id = webhook_manager.register_webhook(
        url=str(subscription.url),
        league_id=subscription.league_id,
        events=subscription.events
    )
    
    return {
        "id": subscription_id,
        "url": str(subscription.url),
        "league_id": subscription.league_id,
        "events": subscription.events,
        "active": True,
        "created_at": datetime.utcnow().isoformat()
    }

@router.get("/", response_model=List[WebhookSubscriptionResponse])
async def list_webhooks(db: Session = Depends(get_db)):
    """Lista todos os webhooks"""
    # Implementação...
    pass

@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Remove um webhook"""
    # Implementação...
    pass
```

### 5. Eventos Disponíveis

**Eventos que podem ser disparados**:

1. `standings_updated` - Tabela de classificação atualizada
2. `fixture_updated` - Partida atualizada (placar mudou, status mudou)
3. `fixture_created` - Nova partida adicionada
4. `top_scorer_updated` - Artilharia atualizada
5. `team_statistics_updated` - Estatísticas de time atualizadas

**Payload exemplo**:

```json
{
  "event": "standings_updated",
  "league_id": 123,
  "data": {
    "league_name": "Brasileirão Série A",
    "updated_at": "2025-01-15T10:30:00Z",
    "standings": [...]
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Processamento Assíncrono de Webhooks**:

```python
# tasks/webhook_tasks.py (NOVO ARQUIVO)
from tasks.celery_app import celery_app
from webhooks.manager import WebhookManager

@celery_app.task(max_retries=3)
def trigger_webhook_task(event_type: str, league_id: int, data: dict):
    """Tarefa assíncrona para disparar webhook"""
    webhook_manager = WebhookManager()
    webhook_manager.trigger_webhook(event_type, league_id, data)
```

---

## 🤖 Sistema de Chatbot

### Arquitetura do Chatbot

**Objetivo**: Permitir consulta de dados via interface conversacional.

### Opção 1: Chatbot com OpenAI/LangChain (Recomendado)

```python
# requirements.txt - Adicionar
langchain>=0.0.350
langchain-openai>=0.0.2
openai>=1.6.0
tiktoken>=0.5.2

# chatbot/chatbot.py (NOVO ARQUIVO)
from langchain.llms import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from typing import Dict, List
import os

from queries import FootballAnalyzer
from config.database import SessionLocal

class FootballChatbot:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.llm = OpenAI(temperature=0, openai_api_key=self.openai_api_key)
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.analyzer = FootballAnalyzer()
        
        # Tools disponíveis para o chatbot
        self.tools = [
            Tool(
                name="get_league_standings",
                func=self._get_league_standings,
                description=(
                    "Obtém a tabela de classificação de uma liga. "
                    "Input: league_id (número inteiro)"
                )
            ),
            Tool(
                name="get_league_top_scorers",
                func=self._get_league_top_scorers,
                description=(
                    "Obtém os artilheiros de uma liga. "
                    "Input: league_id (número inteiro)"
                )
            ),
            Tool(
                name="get_team_statistics",
                func=self._get_team_statistics,
                description=(
                    "Obtém estatísticas de um time. "
                    "Input: team_name (string) e league_id (número inteiro)"
                )
            ),
            Tool(
                name="get_upcoming_fixtures",
                func=self._get_upcoming_fixtures,
                description=(
                    "Obtém próximas partidas de uma liga. "
                    "Input: league_id (número inteiro) e limit (número, opcional)"
                )
            ),
            Tool(
                name="search_league",
                func=self._search_league,
                description=(
                    "Busca uma liga pelo nome. "
                    "Input: league_name (string)"
                )
            ),
        ]
        
        # Inicializa agente com tools
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True
        )
    
    def _get_league_standings(self, league_id: str) -> str:
        """Tool para obter tabela de classificação"""
        try:
            league_id_int = int(league_id)
            standings = self.analyzer.get_league_standings(league_id_int)
            
            if standings.empty:
                return f"Nenhuma classificação encontrada para a liga {league_id}"
            
            # Formata resposta amigável
            result = f"Tabela de Classificação (Liga {league_id}):\n\n"
            for idx, row in standings.head(10).iterrows():
                result += f"{row['rank']}. {row['team_name']} - {row['points']} pontos "
                result += f"({row['wins']}V/{row['draws']}E/{row['losses']}D)\n"
            
            return result
        except Exception as e:
            return f"Erro ao buscar classificação: {str(e)}"
    
    def _get_league_top_scorers(self, league_id: str) -> str:
        """Tool para obter artilheiros"""
        try:
            from main import FootballDataCollector
            collector = FootballDataCollector()
            league_id_int = int(league_id)
            scorers = collector.get_league_top_scorers_from_db(league_id_int)
            
            if not scorers:
                return f"Nenhum artilheiro encontrado para a liga {league_id}"
            
            result = f"Artilheiros da Liga {league_id}:\n\n"
            for i, scorer in enumerate(scorers[:10], 1):
                result += f"{i}. {scorer['jogador-nome']} - {scorer['jogador-gols']} gols "
                result += f"({scorer['jogador-posicao']})\n"
            
            return result
        except Exception as e:
            return f"Erro ao buscar artilheiros: {str(e)}"
    
    def _get_team_statistics(self, input_str: str) -> str:
        """Tool para obter estatísticas de time"""
        # Parse input_str para extrair team_name e league_id
        # Implementação...
        pass
    
    def _get_upcoming_fixtures(self, input_str: str) -> str:
        """Tool para obter próximas partidas"""
        # Implementação...
        pass
    
    def _search_league(self, league_name: str) -> str:
        """Tool para buscar liga por nome"""
        try:
            leagues = self.analyzer.get_available_leagues_from_api()
            matching = [
                l for l in leagues 
                if league_name.lower() in l.get('name', '').lower()
            ]
            
            if not matching:
                return f"Nenhuma liga encontrada com o nome '{league_name}'"
            
            result = f"Ligas encontradas:\n\n"
            for league in matching[:5]:
                result += f"- {league.get('name')} (ID: {league.get('id')}) "
                result += f"- {league.get('country')}\n"
            
            return result
        except Exception as e:
            return f"Erro ao buscar ligas: {str(e)}"
    
    def chat(self, message: str) -> str:
        """Processa mensagem do usuário e retorna resposta"""
        try:
            response = self.agent.run(message)
            return response
        except Exception as e:
            return f"Desculpe, ocorreu um erro: {str(e)}"
```

### Opção 2: Chatbot Simples com Regras (Mais Leve)

```python
# chatbot/simple_chatbot.py (NOVO ARQUIVO)
import re
from typing import Dict, Optional
from queries import FootballAnalyzer
from main import FootballDataCollector

class SimpleFootballChatbot:
    def __init__(self):
        self.analyzer = FootballAnalyzer()
        self.collector = FootballDataCollector()
        self.greetings = ['oi', 'olá', 'hello', 'hi']
        self.help_patterns = [
            r'help', r'ajuda', r'comandos', r'o que você pode fazer'
        ]
    
    def process_message(self, message: str) -> str:
        """Processa mensagem e retorna resposta"""
        message_lower = message.lower().strip()
        
        # Cumprimentos
        if any(greeting in message_lower for greeting in self.greetings):
            return self._get_greeting_response()
        
        # Ajuda
        if any(re.search(pattern, message_lower) for pattern in self.help_patterns):
            return self._get_help_response()
        
        # Buscar classificação
        if re.search(r'(classifica|tabela|standings)', message_lower):
            league_id = self._extract_league_id(message)
            if league_id:
                return self._get_standings_response(league_id)
            return "Por favor, especifique o ID da liga. Ex: 'Tabela da liga 123'"
        
        # Buscar artilheiros
        if re.search(r'(artilh|goleador|top scorer)', message_lower):
            league_id = self._extract_league_id(message)
            if league_id:
                return self._get_top_scorers_response(league_id)
            return "Por favor, especifique o ID da liga."
        
        # Buscar liga
        if re.search(r'(liga|league)', message_lower):
            league_name = self._extract_league_name(message)
            if league_name:
                return self._search_league_response(league_name)
        
        return "Desculpe, não entendi. Digite 'ajuda' para ver os comandos disponíveis."
    
    def _extract_league_id(self, message: str) -> Optional[int]:
        """Extrai ID de liga da mensagem"""
        numbers = re.findall(r'\d+', message)
        if numbers:
            return int(numbers[0])
        return None
    
    def _extract_league_name(self, message: str) -> Optional[str]:
        """Extrai nome de liga da mensagem"""
        # Lógica simples para extrair nome
        # Melhorar com NLP mais avançado se necessário
        pass
    
    def _get_greeting_response(self) -> str:
        return (
            "Olá! 👋 Sou o assistente de futebol.\n"
            "Posso te ajudar com:\n"
            "- Tabelas de classificação\n"
            "- Artilheiros\n"
            "- Estatísticas de times\n"
            "- Próximas partidas\n\n"
            "Digite 'ajuda' para ver todos os comandos."
        )
    
    def _get_help_response(self) -> str:
        return """
📋 **Comandos Disponíveis:**

🏆 **Classificação:**
- "Tabela da liga 123"
- "Classificação liga 123"

⚽ **Artilheiros:**
- "Artilheiros liga 123"
- "Top scorers liga 123"

🔍 **Buscar Liga:**
- "Buscar liga Brasileirão"
- "Liga Premier League"

💬 Digite sua pergunta e eu te ajudo!
        """
    
    def _get_standings_response(self, league_id: int) -> str:
        try:
            standings = self.analyzer.get_league_standings(league_id)
            if standings.empty:
                return f"Nenhuma classificação encontrada para a liga {league_id}"
            
            response = f"🏆 **Classificação - Liga {league_id}:**\n\n"
            for idx, row in standings.head(10).iterrows():
                response += f"{row['rank']}. {row['team_name']} - {row['points']}pts\n"
            
            return response
        except Exception as e:
            return f"Erro ao buscar classificação: {str(e)}"
    
    def _get_top_scorers_response(self, league_id: int) -> str:
        try:
            scorers = self.collector.get_league_top_scorers_from_db(league_id)
            if not scorers:
                return f"Nenhum artilheiro encontrado para a liga {league_id}"
            
            response = f"⚽ **Artilheiros - Liga {league_id}:**\n\n"
            for i, scorer in enumerate(scorers[:10], 1):
                response += f"{i}. {scorer['jogador-nome']} - {scorer['jogador-gols']} gols\n"
            
            return response
        except Exception as e:
            return f"Erro ao buscar artilheiros: {str(e)}"
```

### Integração com API REST

```python
# api/chatbot.py (NOVO ARQUIVO)
from fastapi import APIRouter, Body
from pydantic import BaseModel
from chatbot.chatbot import FootballChatbot, SimpleFootballChatbot

router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

# Opção 1: Chatbot com LLM
@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(message: ChatMessage):
    """Chat com bot usando LLM"""
    chatbot = FootballChatbot()
    response = chatbot.chat(message.message)
    return ChatResponse(
        response=response,
        session_id=message.session_id or "default"
    )

# Opção 2: Chatbot simples
@router.post("/chat/simple", response_model=ChatResponse)
async def chat_simple(message: ChatMessage):
    """Chat com bot simples baseado em regras"""
    chatbot = SimpleFootballChatbot()
    response = chatbot.process_message(message.message)
    return ChatResponse(
        response=response,
        session_id=message.session_id or "default"
    )
```

### Interface Web para Chatbot (Opcional)

```html
<!-- chatbot/web_interface.html (NOVO ARQUIVO) -->
<!DOCTYPE html>
<html>
<head>
    <title>Chatbot - Campeonatos Stats</title>
    <style>
        /* Estilos CSS... */
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-messages" id="chatMessages"></div>
        <div class="chat-input">
            <input type="text" id="messageInput" placeholder="Digite sua pergunta...">
            <button onclick="sendMessage()">Enviar</button>
        </div>
    </div>
    
    <script>
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value;
            if (!message) return;
            
            // Adiciona mensagem do usuário
            addMessage(message, 'user');
            input.value = '';
            
            // Envia para API
            const response = await fetch('/api/v1/chatbot/chat/simple', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: message})
            });
            
            const data = await response.json();
            addMessage(data.response, 'bot');
        }
        
        function addMessage(text, sender) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            messageDiv.textContent = text;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    </script>
</body>
</html>
```

---

## 📊 Monitoramento e Métricas

### Implementar Observabilidade

```python
# requirements.txt - Adicionar
prometheus-client>=0.19.0
sentry-sdk>=1.38.0

# monitoring/metrics.py (NOVO ARQUIVO)
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# Métricas
api_requests_total = Counter(
    'api_requests_total',
    'Total de requisições API',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'Duração de requisições API',
    ['endpoint']
)

data_collection_jobs = Counter(
    'data_collection_jobs_total',
    'Total de jobs de coleta',
    ['league_id', 'status']
)

cache_hits = Counter(
    'cache_hits_total',
    'Total de cache hits',
    ['cache_key']
)

# Middleware para coletar métricas
@app.middleware("http")
async def collect_metrics(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    api_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    api_request_duration.labels(
        endpoint=request.url.path
    ).observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    """Endpoint Prometheus para métricas"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

---

## 📦 Deploy e Infraestrutura

### Docker Compose para Ambiente Completo

```yaml
# docker-compose.yml (NOVO ARQUIVO)
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: campeonatos_stats
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  
  api:
    build: .
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5432/campeonatos_stats
      REDIS_HOST: redis
    depends_on:
      - postgres
      - redis
  
  celery-worker:
    build: .
    command: celery -A tasks.celery_app worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5432/campeonatos_stats
      REDIS_HOST: redis
    depends_on:
      - postgres
      - redis
  
  celery-beat:
    build: .
    command: celery -A tasks.celery_app beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5432/campeonatos_stats
      REDIS_HOST: redis
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
```

### Dockerfile

```dockerfile
# Dockerfile (NOVO ARQUIVO)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📝 Checklist de Implementação

### Fase 1: Otimizações de Banco (Prioridade Alta)
- [ ] Migrar para PostgreSQL
- [ ] Configurar connection pooling
- [ ] Adicionar índices
- [ ] Criar migrations com Alembic
- [ ] Testar performance

### Fase 2: Cache e Performance (Prioridade Alta)
- [ ] Configurar Redis
- [ ] Implementar CacheManager
- [ ] Adicionar decorators @cached
- [ ] Invalidar cache apropriadamente

### Fase 3: Processamento Assíncrono (Prioridade Média)
- [ ] Configurar Celery ou RQ
- [ ] Migrar coletas para tasks assíncronas
- [ ] Configurar workers
- [ ] Testar processamento paralelo

### Fase 4: API REST (Prioridade Alta)
- [ ] Criar estrutura FastAPI
- [ ] Implementar endpoints principais
- [ ] Adicionar rate limiting
- [ ] Documentação Swagger
- [ ] Testes de API

### Fase 5: Sistema de Webhooks (Prioridade Média)
- [ ] Criar tabelas de webhooks
- [ ] Implementar WebhookManager
- [ ] Integrar com coleta de dados
- [ ] Criar endpoints de gerenciamento
- [ ] Testar disparo de webhooks

### Fase 6: Chatbot (Prioridade Baixa)
- [ ] Escolher abordagem (LLM ou regras)
- [ ] Implementar chatbot
- [ ] Integrar com API
- [ ] Criar interface web (opcional)
- [ ] Testar interações

### Fase 7: Monitoramento (Prioridade Média)
- [ ] Configurar métricas Prometheus
- [ ] Integrar Sentry para erros
- [ ] Configurar logs estruturados
- [ ] Dashboards de monitoramento

### Fase 8: Deploy (Prioridade Alta)
- [ ] Criar Docker Compose
- [ ] Configurar variáveis de ambiente
- [ ] Testar em ambiente de staging
- [ ] Deploy em produção

---

## 🔐 Segurança

### Boas Práticas

1. **Autenticação de Webhooks**:
   - Sempre validar assinatura HMAC
   - Verificar timestamp para prevenir replay attacks

2. **Rate Limiting**:
   - Limitar requisições por IP
   - Limitar requisições por API key (se implementar)

3. **Validação de Dados**:
   - Validar todos os inputs com Pydantic
   - Sanitizar dados antes de inserir no banco

4. **Secrets Management**:
   - Usar variáveis de ambiente
   - Considerar AWS Secrets Manager ou similar em produção

---

## 📚 Referências e Recursos

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Documentation](https://redis.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [LangChain Documentation](https://python.langchain.com/)
- [Prometheus Documentation](https://prometheus.io/docs/)

---

**Última atualização**: 2025-01-15
