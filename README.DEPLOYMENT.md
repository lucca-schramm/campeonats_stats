# 🚀 Guia de Deploy - Desenvolvimento vs Produção

## 📋 Estrutura de Ambientes

O projeto está configurado para suportar dois ambientes distintos:

### 🔧 Desenvolvimento
- **Arquivo**: `docker-compose.dev.yml`
- **Uso**: `docker-compose -f docker-compose.dev.yml up`
- **Características**:
  - Hot reload ativado (`--reload` no uvicorn)
  - Volumes montados para edição em tempo real
  - Portas expostas para debug
  - Logs detalhados
  - Frontend com Vite dev server

### 🏭 Produção
- **Arquivo**: `docker-compose.prod.yml`
- **Uso**: `docker-compose -f docker-compose.prod.yml up -d`
- **Características**:
  - Sem hot reload (otimizado)
  - Múltiplos workers (4 workers)
  - Portas não expostas externamente (apenas via nginx)
  - Redis com senha
  - Logs reduzidos (warning apenas)
  - Frontend buildado e otimizado
  - Gzip compression
  - Cache de assets estáticos

## 🔄 Como Usar

### Desenvolvimento

```bash
# Iniciar ambiente de desenvolvimento
docker-compose -f docker-compose.dev.yml up

# Ou usar o arquivo padrão (já configurado para dev)
docker-compose up
```

### Produção

```bash
# 1. Configure variáveis de ambiente em .env
cp .env.example .env
# Edite .env com valores de produção

# 2. Build das imagens
docker-compose -f docker-compose.prod.yml build

# 3. Iniciar em background
docker-compose -f docker-compose.prod.yml up -d

# 4. Ver logs
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔐 Variáveis de Ambiente Importantes

### Desenvolvimento
```env
DEBUG=True
ENVIRONMENT=development
CACHE_TTL=120
```

### Produção
```env
DEBUG=False
ENVIRONMENT=production
CACHE_TTL=300
DB_PASSWORD=<senha_forte>
REDIS_PASSWORD=<senha_forte>
RABBITMQ_PASSWORD=<senha_forte>
SECRET_KEY=<chave_32_caracteres>
ENCRYPTION_KEY=<chave_32_caracteres>
```

## 📝 Diferenças Principais

| Aspecto | Desenvolvimento | Produção |
|---------|----------------|----------|
| **API Reload** | ✅ Sim (`--reload`) | ❌ Não (4 workers) |
| **Volumes** | ✅ Montados | ❌ Não (imagem buildada) |
| **Portas Expostas** | ✅ Todas | ❌ Apenas frontend |
| **Logs** | ✅ Detalhados (info) | ⚠️ Reduzidos (warning) |
| **Frontend** | 🔥 Vite dev server | 📦 Nginx com build |
| **Cache TTL** | 120s (2 min) | 300s (5 min) |
| **Segurança** | Básica | Reforçada |
| **Workers Celery** | 4 | 8 |

## 🛠️ Comandos Úteis

### Desenvolvimento
```bash
# Rebuild apenas frontend
docker-compose -f docker-compose.dev.yml build frontend

# Ver logs em tempo real
docker-compose -f docker-compose.dev.yml logs -f api

# Reiniciar apenas API
docker-compose -f docker-compose.dev.yml restart api
```

### Produção
```bash
# Atualizar código (rebuild necessário)
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Backup do banco
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres campeonatos_stats > backup.sql

# Verificar saúde dos serviços
docker-compose -f docker-compose.prod.yml ps
```

## 📦 Build do Frontend

O frontend é buildado automaticamente no Dockerfile, mas você pode buildar manualmente:

```bash
cd frontend
npm install
npm run build
```

## 🔒 Checklist de Produção

Antes de fazer deploy em produção, verifique:

- [ ] Todas as senhas alteradas (DB, Redis, RabbitMQ)
- [ ] `DEBUG=False` no .env
- [ ] `ENVIRONMENT=production` no .env
- [ ] `SECRET_KEY` gerada (mínimo 32 caracteres)
- [ ] `ENCRYPTION_KEY` gerada (32 caracteres)
- [ ] CORS_ORIGINS configurado com domínio de produção
- [ ] `REDIS_PASSWORD` configurado
- [ ] Backup do banco configurado
- [ ] Logs configurados para rotação
- [ ] Monitoramento configurado

## 🌐 Nginx em Produção

O nginx em produção inclui:
- Gzip compression
- Cache de assets estáticos (1 ano)
- Headers de segurança
- Timeouts otimizados

