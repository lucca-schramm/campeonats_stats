# 🚀 Guia de Deploy e Comandos

Este documento lista todos os comandos npm disponíveis para gerenciar a aplicação.

## 📦 Deploy

### Frontend
```bash
npm run deploy:frontend    # Para e reconstrói o frontend
```

### API/Chatbot
```bash
npm run deploy:api         # Para e reconstrói a API
npm run deploy:chat        # Alias para deploy:api
npm run deploy:chatbot     # Alias para deploy:api
```

### Completo
```bash
npm run deploy:all         # Para tudo, reconstrói e inicia todos os serviços
npm run deploy:dev         # Deploy em modo desenvolvimento
npm run deploy:prod        # Deploy em modo produção
```

## 🔄 Restart (com rebuild)

**IMPORTANTE**: Os comandos `restart` fazem rebuild completo (down → build → up) para garantir que mudanças no código sejam aplicadas.

### Serviços Individuais
```bash
npm run restart:frontend   # Para, reconstrói e inicia o frontend
npm run restart:api        # Para, reconstrói e inicia a API
npm run restart:chat       # Alias para restart:api (chatbot)
npm run restart:chatbot    # Alias para restart:api (chatbot)
npm run restart:services   # Para, reconstrói e inicia API, Celery Worker e Beat
npm run restart:db         # Reinicia apenas PostgreSQL e Redis (sem rebuild)
```

### Todos os Serviços
```bash
npm run restart:all        # Para tudo, reconstrói e inicia todos os serviços
```

### Quick (sem parar, apenas rebuild e up)
```bash
npm run quick:frontend     # Rebuild e up do frontend (sem parar)
npm run quick:api          # Rebuild e up da API (sem parar)
npm run quick:chat         # Rebuild e up da API/chatbot (sem parar)
```

## ⏹️ Stop

```bash
npm run stop:frontend      # Para o frontend
npm run stop:api           # Para a API
npm run stop:chat          # Alias para stop:api
npm run stop:chatbot       # Alias para stop:api
npm run stop:all           # Para todos os serviços
```

## ▶️ Start

```bash
npm run start:frontend     # Inicia o frontend
npm run start:api          # Inicia a API
npm run start:chat         # Alias para start:api
npm run start:chatbot      # Alias para start:api
npm run start:all          # Inicia todos os serviços
```

## 📋 Logs

```bash
npm run logs:frontend      # Logs do frontend (seguir)
npm run logs:api           # Logs da API (seguir)
npm run logs:chat          # Alias para logs:api
npm run logs:chatbot       # Alias para logs:api
npm run logs:all           # Logs de todos os serviços
npm run logs:db            # Logs do PostgreSQL e Redis
npm run logs:celery        # Logs do Celery Worker e Beat
```

## 🔨 Build

```bash
npm run build:frontend     # Constrói apenas o frontend
npm run build:api          # Constrói apenas a API
npm run build:chat         # Alias para build:api
npm run build:chatbot      # Alias para build:api
npm run build:all          # Constrói todos os serviços
```

## 📊 Status e Health

```bash
npm run status             # Mostra status de todos os containers
npm run health             # Verifica saúde dos containers
npm run health:api         # Health check específico da API
```

## 🧹 Limpeza

```bash
npm run clean              # Remove containers e volumes
npm run clean:all          # Remove containers, volumes e limpa sistema Docker
npm run clean:images       # Remove imagens do projeto
```

## 🐚 Shell/Console

```bash
npm run shell:api          # Abre shell no container da API
npm run shell:frontend     # Abre shell no container do frontend
npm run shell:db           # Abre psql no PostgreSQL
```

## 🧪 Testes

```bash
npm run test:api           # Executa testes da API
npm run test:frontend      # Executa lint do frontend
```

## 💾 Banco de Dados

```bash
npm run db:backup          # Cria backup do banco de dados
npm run db:restore         # Mostra comando para restaurar backup
```

## 🎯 Setup Inicial

```bash
npm run init               # Inicia serviços base (DB, Redis, RabbitMQ) e depois todos
npm run setup              # Alias para init
```

## 📝 Exemplos de Uso

### Deploy completo após mudanças no código
```bash
npm run deploy:all
```

### Apenas atualizar frontend após mudanças
```bash
npm run deploy:frontend
```

### Reiniciar apenas o chatbot após mudanças no código
```bash
npm run restart:chat
```

### Ver logs do chatbot em tempo real
```bash
npm run logs:chat
```

### Verificar status de todos os serviços
```bash
npm run status
```

### Deploy em produção
```bash
npm run deploy:prod
```

### Deploy em desenvolvimento
```bash
npm run deploy:dev
```

