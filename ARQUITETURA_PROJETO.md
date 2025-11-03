# 🏗️ Arquitetura do Projeto - Campeonatos Stats

## 📐 Visão Geral

Sistema completo de coleta, armazenamento e visualização de dados de futebol com arquitetura moderna, escalável e profissional.

## 🎯 Stack Tecnológica

### Backend
- **FastAPI** - Framework web assíncrono e moderno
- **PostgreSQL** - Banco de dados relacional (único banco usado)
- **SQLAlchemy** - ORM para acesso ao banco
- **Redis** - Cache e broker para Celery
- **Celery** - Processamento assíncrono de tarefas
- **Pydantic** - Validação de dados

### Frontend
- **Vue.js 3** - Framework JavaScript reativo
- **Vue Router** - Roteamento SPA
- **Axios** - Cliente HTTP
- **Tailwind CSS** - Framework CSS utilitário
- **Vite** - Build tool moderna

### Infraestrutura
- **Docker** - Containerização
- **Docker Compose** - Orquestração de serviços
- **Nginx** - Servidor web para frontend

## 📁 Estrutura de Diretórios

```
campeonatos_stats/
├── app/                          # Backend FastAPI
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/        # Endpoints REST organizados
│   │       │   ├── chatbot.py   # API do chatbot
│   │       │   ├── collection.py # Controle de coleta
│   │       │   ├── leagues.py    # API de ligas
│   │       │   ├── webhooks.py   # Webhooks
│   │       │   └── data_integrity.py # Validação
│   │       └── api.py            # Router principal
│   ├── core/                     # Configurações centrais
│   │   ├── config.py             # Settings (Pydantic)
│   │   ├── database.py           # Config PostgreSQL
│   │   ├── cache.py              # Redis cache
│   │   ├── middleware.py         # Middlewares customizados
│   │   └── logging_config.py    # Logging
│   ├── models/                   # Modelos SQLAlchemy (PostgreSQL)
│   │   ├── base.py               # BaseModel comum
│   │   ├── league.py             # League
│   │   ├── team.py               # Team
│   │   ├── fixture.py            # Fixture
│   │   ├── player.py             # Player
│   │   ├── team_statistics.py    # TeamStatistics
│   │   └── match_player.py       # MatchPlayer
│   ├── services/                 # Lógica de negócio
│   │   ├── collection_service.py # Serviço de coleta inteligente
│   │   └── league_service.py     # Serviço de ligas
│   ├── repositories/              # Camada de acesso a dados
│   │   └── league_repository.py  # Repository pattern
│   ├── chatbot/                  # Serviço de chatbot
│   │   └── service.py            # Chatbot rule-based
│   ├── webhooks/                 # Sistema de webhooks
│   │   └── manager.py            # Gerenciador de webhooks
│   ├── tasks/                    # Tarefas Celery
│   │   ├── celery_app.py        # Config Celery
│   │   ├── data_collection.py    # Task de coleta
│   │   └── scheduler.py          # Agendamento (Celery Beat)
│   ├── schemas/                  # Schemas Pydantic
│   │   ├── chatbot.py
│   │   ├── league.py
│   │   └── webhook.py
│   └── main.py                   # Aplicação FastAPI principal
│
├── main.py                        # Coletor de dados (FootyStats API)
│                                   # - FootyStatsAPIClient
│                                   # - FootballDataCollector (PostgreSQL)
│
├── frontend/                      # Frontend Vue.js
│   ├── src/
│   │   ├── views/                # Páginas
│   │   │   ├── LeaguesView.vue   # Lista de ligas
│   │   │   ├── LeagueView.vue    # Visualização de liga (genérico)
│   │   │   ├── BrasileiraoView.vue # Brasileirão específico
│   │   │   └── ChatbotView.vue   # Chatbot
│   │   ├── components/           # Componentes reutilizáveis
│   │   │   ├── BrasileiraoStats.vue
│   │   │   ├── BrasileiraoTable.vue
│   │   │   └── BrasileiraoTopScorers.vue
│   │   ├── router/               # Vue Router
│   │   │   └── index.js
│   │   └── App.vue               # Componente raiz
│   └── package.json
│
├── tests/                         # Testes automatizados
├── scripts/                       # Scripts utilitários
├── docker-compose.yml             # Orquestração Docker
├── Dockerfile                     # Backend container
├── requirements.txt               # Dependências Python
└── README.md                      # Documentação principal
```

## 🔄 Fluxo de Dados

### 1. Coleta de Dados (FootyStats API)

```
FootyStats API
    ↓
FootyStatsAPIClient (main.py)
    ↓
FootballDataCollector (main.py)
    ↓
PostgreSQL (via SQLAlchemy)
    ├── League
    ├── Team
    ├── Fixture
    ├── Player
    └── TeamStatistics
```

**Agendamento:**
- **Celery Beat** → `scheduled_collection()` (a cada 15 min)
- **CollectionService** → Determina ligas prioritárias
- **Celery Worker** → `collect_league_data_task()` (assíncrono)

### 2. API REST (FastAPI)

```
Frontend/Cliente
    ↓
FastAPI (app/main.py)
    ↓
Endpoints (app/api/v1/endpoints/)
    ↓
Services (app/services/)
    ↓
Repositories (app/repositories/) [opcional]
    ↓
Models (app/models/) + SQLAlchemy
    ↓
PostgreSQL
```

### 3. Chatbot

```
Usuário
    ↓
ChatbotView.vue (Frontend)
    ↓
POST /api/v1/chatbot/chat
    ↓
ChatbotService (app/chatbot/service.py)
    ↓
Query PostgreSQL (via SQLAlchemy)
    ↓
Resposta formatada
```

## 🗄️ Banco de Dados

### PostgreSQL (Único Banco)

**Modelos:**
- `League` - Ligas e campeonatos
- `Team` - Times
- `Fixture` - Partidas
- `Player` - Jogadores
- `TeamStatistics` - Estatísticas de times (tabela de classificação)
- `MatchPlayer` - Jogadores por partida
- `WebhookLog` - Logs de webhooks
- `WebhookSubscription` - Assinaturas de webhooks

**Configuração:**
- Connection Pool: 50 conexões, max_overflow=100
- Pool Pre-ping: Ativado
- Pool Recycle: 1 hora

## 🔐 Segurança e Performance

### Rate Limiting
- Global: 1000/hora, 100/minuto por IP
- Endpoints específicos: 200/minuto (standings), 100/minuto (chatbot)

### Cache (Redis)
- TTL: 120 segundos (2 minutos)
- Endpoints cacheados: `/leagues/*`, `/chatbot/*`

### Middlewares
1. **PerformanceMiddleware** - Medição de tempo de resposta
2. **SecurityHeadersMiddleware** - Headers de segurança
3. **GZipMiddleware** - Compressão de respostas (~70% redução)
4. **CORSMiddleware** - Controle de acesso cross-origin

## 📊 Coleta de Dados

### Endpoints FootyStats Utilizados

1. **`league-list`** (chosen_leagues_only=true)
   - Lista ligas configuradas na conta

2. **`league-teams`**
   - Times de uma temporada

3. **`league-matches`**
   - Partidas de uma temporada

4. **`league-players`**
   - Jogadores com paginação automática

### Processo de Coleta

1. **Carrega ligas** da API FootyStats
2. **Coleta times** para cada liga
3. **Coleta partidas** (fixtures)
4. **Coleta jogadores** (com paginação)
5. **Calcula tabela** de classificação
6. **Dispara webhooks** (opcional)

### Agendamento Inteligente

- **Alta prioridade**: Ligas com jogos ao vivo
- **Média prioridade**: Ligas com jogos nas próximas 30min
- **Baixa prioridade**: Outras ligas (coleta periódica)

## 🎨 Frontend

### Rotas

- `/` → Redireciona para `/ligas`
- `/ligas` → Lista de ligas disponíveis
- `/ligas/:leagueId` → Visualização de liga específica
- `/chatbot` → Interface do chatbot

### Componentes

- **BrasileiraoStats** - Estatísticas (geral/casa/fora)
- **BrasileiraoTable** - Tabela de classificação
- **BrasileiraoTopScorers** - Artilheiros

### Design

- **Tailwind CSS** - Design responsivo
- **Gradientes** - Visual moderno
- **Navegação** - Barra global no App.vue

## 🧪 Testes

- **run_tests.py** - Suite de testes
- **tests/** - Testes automatizados
- **scripts/test_api.sh/ps1** - Scripts de teste

## ✅ Melhores Práticas Implementadas

1. **Separação de Responsabilidades**
   - Models → Dados
   - Services → Lógica de negócio
   - Repositories → Acesso a dados (quando necessário)
   - Endpoints → Controllers

2. **PostgreSQL Único**
   - ✅ Removido SQLite completamente
   - ✅ Todas as operações via SQLAlchemy
   - ✅ Connection pooling otimizado

3. **Cache Estratégico**
   - Redis para endpoints frequentes
   - TTL configurável

4. **Processamento Assíncrono**
   - Celery para tarefas pesadas
   - Não bloqueia API

5. **Validação de Dados**
   - Pydantic schemas
   - Validação de integridade

6. **Documentação**
   - FastAPI docs automáticos (/docs)
   - README completo

## 🚀 Escalabilidade

- **Connection Pooling**: 50 conexões + 100 overflow
- **Cache Redis**: Reduz carga no PostgreSQL
- **Celery Workers**: Processamento paralelo
- **Rate Limiting**: Proteção contra abuso
- **Compressão GZip**: Reduz bandwidth

## 📝 Notas Importantes

- ✅ **100% PostgreSQL** - Nenhuma referência SQLite
- ✅ **Arquitetura limpa** - Separação clara de responsabilidades
- ✅ **Escalável** - Preparado para alta carga
- ✅ **Profissional** - Padrões de código modernos
- ✅ **Documentado** - Código e estrutura bem documentados

