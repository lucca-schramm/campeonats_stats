# Campeonatos Stats - Sistema Completo

Sistema completo para coleta, armazenamento e visualização de dados de futebol com API REST, frontend Vue.js e chatbot interativo.

## 🏗️ Estrutura do Projeto (Monorepo)

```
campeonatos_stats/
├── app/                    # Backend FastAPI
│   ├── api/v1/endpoints/  # Endpoints REST
│   ├── core/              # Configurações core
│   ├── models/            # Modelos SQLAlchemy
│   ├── services/          # Lógica de negócio
│   ├── repositories/       # Camada de acesso a dados
│   ├── chatbot/           # Serviço de chatbot
│   └── webhooks/          # Sistema de webhooks
├── frontend/              # Frontend Vue.js + Tailwind
│   ├── src/
│   │   ├── views/        # Páginas
│   │   ├── components/   # Componentes Vue
│   │   └── router/       # Rotas
│   └── package.json
├── tests/                 # Testes automatizados
└── docker-compose.yml     # Orquestração de serviços
```

## 🚀 Início Rápido

### Pré-requisitos

- **Docker Desktop** instalado e rodando
- Docker Compose (incluído no Docker Desktop)

### Executar Tudo com Docker

```bash
# 1. Iniciar todos os serviços
docker-compose up -d

# 2. Verificar logs
docker-compose logs -f
```

### Acessar Aplicação

Após os containers iniciarem:

- **Frontend**: http://localhost:3000
- **API Backend**: http://localhost:8000
- **Documentação API**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Comandos Úteis

```bash
# Parar todos os serviços
docker-compose down

# Parar e remover volumes (limpar dados)
docker-compose down -v

# Rebuild dos containers
docker-compose build --no-cache

# Ver logs de um serviço específico
docker-compose logs -f api
docker-compose logs -f frontend
```

## 📋 Funcionalidades

### Backend (FastAPI)

- ✅ **API REST** completa com endpoints organizados
- ✅ **Redis Cache** com TTL de 2 minutos
- ✅ **Validação de Integridade** de dados
- ✅ **Rate Limiting** configurável
- ✅ **Webhooks** para notificações
- ✅ **Chatbot** interativo
- ✅ **Connection Pooling** otimizado

### Frontend (Vue.js)

- ✅ **Visualização Brasileirão** com estatísticas
- ✅ **Tabela de Classificação** interativa
- ✅ **Top Artilheiros** com ranking
- ✅ **Chatbot** integrado
- ✅ **Design Responsivo** com Tailwind CSS
- ✅ **Navegação** com Vue Router

## ⚙️ Configurações

### Redis Cache

Cache configurado para **2 minutos (120 segundos)** em todos os endpoints:

- `/api/v1/leagues/*` - 120s
- `/api/v1/chatbot/*` - 120s
- `/api/v1/webhooks/*` - 120s

### Integridade de Dados

Sistema de validação implementado em `app/core/data_integrity.py`:

- Validação de ligas
- Validação de estatísticas de times
- Validação de jogadores
- Validação de partidas
- Verificação de consistência

Endpoint: `GET /api/v1/data-integrity/check`

### Rate Limiting

- Global: 1000/hora, 100/minuto por IP
- Standings: 200/minuto
- Chatbot: 100/minuto

## 🧪 Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Executar com cobertura
pytest tests/ --cov=app --cov-report=html
```

## 📦 Estrutura de Dados

### Modelos Principais

- **League**: Ligas e campeonatos
- **Team**: Times
- **Fixture**: Partidas
- **Player**: Jogadores e artilheiros
- **TeamStatistics**: Estatísticas de times

## 🔐 Variáveis de Ambiente

Crie um arquivo `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/campeonatos_stats
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL=120
FOOTYSTATS_API_KEY=sua_chave_aqui
OPENAI_API_KEY=sua_chave_openai
DEBUG=True
```

## 📚 Documentação da API

Acesse `/docs` para documentação interativa gerada automaticamente pelo FastAPI.

## 🐳 Docker

O projeto está **100% containerizado** e roda completamente no Docker Desktop.

### Serviços Disponíveis

- **frontend**: Porta 3000 (Nginx servindo Vue.js)
- **api**: Porta 8000 (FastAPI)
- **postgres**: Porta 5432 (PostgreSQL)
- **redis**: Porta 6379 (Redis Cache)
- **celery-worker**: Processamento assíncrono
- **celery-beat**: Agendamento de tarefas

### Estrutura Docker

Todos os serviços estão conectados na mesma rede Docker (`app-network`) e podem se comunicar internamente.

## 📝 Licença

Este projeto é privado e proprietário.