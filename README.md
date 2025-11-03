# Campeonatos Stats - Sistema de Coleta de Dados de Futebol

Sistema para coleta, armazenamento e exportação de dados de futebol utilizando a API FootyStats.

## 🎯 Objetivo

Coletar dados de ligas, times, partidas e estatísticas das ligas disponíveis no FootyStats, armazenar em banco de dados SQLite e exportar no formato JSON especificado.

## 🔧 Configuração

### 1. Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com:

```env
FOOTYSTATS_API_KEY=sua_chave_api_aqui
```

### 2. Instalação de Dependências

```bash
pip install -r requirements.txt
```

### 3. Estrutura do Banco de Dados

O sistema cria automaticamente as seguintes tabelas:

#### `leagues` - Ligas
- `id` (INTEGER PRIMARY KEY) - ID único da liga
- `name` (TEXT) - Nome da liga
- `country` (TEXT) - País da liga
- `image` (TEXT) - URL da imagem da liga
- `season_id` (INTEGER) - ID da temporada
- `season_year` (INTEGER) - Ano da temporada

#### `teams` - Times
- `id` (INTEGER PRIMARY KEY) - ID único do time
- `name` (TEXT) - Nome do time
- `logo` (TEXT) - URL do logo do time
- `league_id` (INTEGER) - ID da liga
- `season_id` (INTEGER) - ID da temporada

#### `fixtures` - Partidas
- `id` (INTEGER PRIMARY KEY) - ID único da partida
- `league_id` (INTEGER) - ID da liga
- `season_id` (INTEGER) - ID da temporada
- `home_team_id` (INTEGER) - ID do time mandante
- `away_team_id` (INTEGER) - ID do time visitante
- `home_team_name` (TEXT) - Nome do time mandante
- `away_team_name` (TEXT) - Nome do time visitante
- `referee` (TEXT) - Árbitro
- `venue_id` (INTEGER) - ID do estádio
- `venue_name` (TEXT) - Nome do estádio
- `venue_city` (TEXT) - Cidade do estádio
- `date` (TEXT) - Data da partida
- `timestamp` (INTEGER) - Timestamp Unix
- `status` (TEXT) - Status da partida
- `home_goals` (INTEGER) - Gols do time mandante
- `away_goals` (INTEGER) - Gols do time visitante
- `home_halftime_goals` (INTEGER) - Gols do mandante no 1º tempo
- `away_halftime_goals` (INTEGER) - Gols do visitante no 1º tempo
- `home_score` (INTEGER) - Placar final do mandante
- `away_score` (INTEGER) - Placar final do visitante
- `home_halftime_score` (INTEGER) - Placar do 1º tempo do mandante
- `away_halftime_score` (INTEGER) - Placar do 1º tempo do visitante

#### `team_statistics` - Estatísticas dos Times
- `id` (INTEGER PRIMARY KEY) - ID único
- `team_id` (INTEGER) - ID do time
- `league_id` (INTEGER) - ID da liga
- `season_id` (INTEGER) - ID da temporada
- `season_year` (INTEGER) - Ano da temporada
- `matches_played` (INTEGER) - Partidas jogadas
- `wins` (INTEGER) - Vitórias
- `draws` (INTEGER) - Empates
- `losses` (INTEGER) - Derrotas
- `goals_for` (INTEGER) - Gols marcados
- `goals_against` (INTEGER) - Gols sofridos
- `points` (INTEGER) - Pontos
- `rank` (INTEGER) - Posição na tabela
- `position` (INTEGER) - Posição na tabela

## 🚀 Como Usar

### Execução Principal

```bash
python main.py
```

### Teste da API

```bash
python test_api.py
```

## 📊 Funcionamento

### 1. Coleta de Ligas
- Obtém ligas escolhidas da API FootyStats usando `chosen_leagues_only=true`
- Identifica automaticamente a temporada mais recente disponível
- Gera IDs únicos para cada liga baseado em hash do nome, país e ano

### 2. Coleta de Dados por Liga
- **Times**: Obtém todos os times da temporada
- **Partidas**: Coleta todas as partidas da temporada
- **Tabela de Classificação**: Constrói automaticamente a partir dos dados de partidas coletados

### 3. Mapeamento de Dados da API

#### Liga (league-list)
```json
{
  "name": "Germany Bundesliga",
  "image": "https://cdn.footystats.org/img/competitions/germany-bundesliga.png",
  "country": "Germany",
  "season": [
    {
      "id": 14968,
      "year": 20252026,
      "country": "Germany"
    }
  ]
}
```

#### Time (league-teams)
```json
{
  "id": 33,
  "name": "BVB 09 Borussia Dortmund",
  "image": "https://cdn.footystats.org/img/teams/germany-bvb-09-borussia-dortmund.png"
}
```

#### Partida (league-matches)
```json
{
  "id": 8227534,
  "homeID": 46,
  "awayID": 552,
  "home_name": "RB Leipzig",
  "away_name": "Heidenheim",
  "status": "complete",
  "homeGoalCount": 2,
  "awayGoalCount": 0,
  "ht_goals_team_a": 0,
  "ht_goals_team_b": 0,
  "date_unix": 1756560600,
  "stadium_name": "Red Bull Arena",
  "stadium_location": "Leipzig"
}
```

## 🔄 Processo de Coleta

1. **Inicialização**: Cria banco de dados e tabelas
2. **Carregamento de Ligas**: Obtém ligas escolhidas da API
3. **Processamento por Liga**:
   - Salva dados da liga
   - Coleta e salva times
   - Constrói tabela de classificação
   - Coleta e salva partidas
4. **Exportação**: Gera arquivos JSON no formato especificado

## 📁 Estrutura de Arquivos

```
campeonatos_stats/
├── main.py                 # Script principal
├── test_api.py            # Teste da API
├── queries.py             # Consultas SQL
├── setup.py               # Configuração do projeto
├── requirements.txt       # Dependências
├── .env                   # Variáveis de ambiente
├── football_stats.db      # Banco de dados SQLite
├── example.json           # Exemplo de formato de saída
└── README.md              # Este arquivo
```

## 🎯 Características Principais

- ✅ **Coleta Automática**: Identifica temporadas mais recentes automaticamente
- ✅ **Dados Completos**: Coleta times, partidas e constrói estatísticas
- ✅ **Mapeamento Correto**: Campos da API FootyStats mapeados corretamente
- ✅ **Tabela de Classificação**: Construída automaticamente a partir dos dados
- ✅ **Tratamento de Erros**: Logs detalhados e tratamento de exceções
- ✅ **Exportação JSON**: Formato compatível com especificação

## 🔧 Configurações da API

### Endpoints Utilizados
- `league-list` - Lista de ligas escolhidas
- `league-teams` - Times de uma temporada
- `league-matches` - Partidas de uma temporada

### Parâmetros
- `chosen_leagues_only=true` - Apenas ligas escolhidas
- `season={season_id}` - ID da temporada
- `league_id={season_id}` - ID da liga (mesmo que season_id)

## 📝 Logs

O sistema gera logs detalhados com:
- Progresso da coleta
- Número de registros processados
- Erros e avisos
- Estatísticas de execução

## 🚨 Observações Importantes

1. **Temporadas**: O sistema sempre busca a temporada mais recente disponível
2. **IDs Únicos**: Liga IDs são gerados usando hash para evitar conflitos
3. **Dados Completos**: Todos os campos disponíveis na API são mapeados
4. **Performance**: Inclui delays para não sobrecarregar a API
5. **Robustez**: Tratamento de erros e validação de dados

## 📊 Exemplo de Saída

O sistema gera arquivos JSON no formato:

```json
{
  "league": {
    "name": "Germany Bundesliga",
    "country": "Germany",
    "season": "20252026"
  },
  "teams": [...],
  "fixtures": [...],
  "standings": [...]
}
```


