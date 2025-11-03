import os
import requests
import sqlite3
import json
import time
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import logging
import base64

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configurações da API
API_BASE_URL = "https://v3.football.api-sports.io"
API_KEY = os.getenv("APISPORTS_KEY")

if not API_KEY:
    raise ValueError("APISPORTS_KEY não configurada no arquivo .env")

# Configurações do banco de dados
DB_NAME = "football_stats.db"

# ⚙️ CONFIGURAÇÕES GIT
GITHUB_USER = "lucca-schramm"
GITHUB_REPO = "test"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BRANCH = "main"

@dataclass
class LeagueConfig:
    """Configuração de uma liga"""
    id: int
    name: str
    country: str
    season: int = 2025

# Configurações das ligas - Agrupadas por competição
LEAGUE_GROUPS = [
    {
        "id": "brasileirao_a",
        "leagues": [
            LeagueConfig(71, "Serie A", "Brazil", 2025),
        ],
        "output_filename": "brasileirao_a.json"
    }
    ,{
        "id": "brasileirao_b", 
        "leagues": [
            LeagueConfig(72, "Serie B", "Brazil", 2025)
        ],
        "output_filename": "brasileirao_b.json"
    }
    ,{
        "id": "bundesliga", 
        "leagues": [
            LeagueConfig(78, "Bundesliga", "Germany", 2025)
        ],
        "output_filename": "bundesliga.json"
    },{
        "id": "sauditao", 
        "leagues": [
            LeagueConfig(307, "Pro League", "Saudi-Arabia", 2025)
        ],
        "output_filename": "sauditao.json"
    }
]

# Mantém a lista simples para compatibilidade com o coletor
LEAGUES = [league for group in LEAGUE_GROUPS for league in group["leagues"]]

class FootballDatabase:
    """Classe para gerenciar o banco de dados SQLite"""
    
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Inicializa as tabelas do banco de dados"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Tabela de ligas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leagues (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    country TEXT NOT NULL,
                    logo TEXT,
                    flag TEXT,
                    season INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de times
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    logo TEXT,
                    league_id INTEGER,
                    FOREIGN KEY (league_id) REFERENCES leagues (id)
                )
            """)
            
            # Tabela de partidas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fixtures (
                    id INTEGER PRIMARY KEY,
                    league_id INTEGER,
                    home_team_id INTEGER,
                    away_team_id INTEGER,
                    referee TEXT,
                    venue_id INTEGER,
                    venue_name TEXT,
                    venue_city TEXT,
                    date TEXT,
                    timestamp INTEGER,
                    status TEXT,
                    home_goals INTEGER,
                    away_goals INTEGER,
                    home_halftime_goals INTEGER,
                    away_halftime_goals INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (league_id) REFERENCES leagues (id),
                    FOREIGN KEY (home_team_id) REFERENCES teams (id),
                    FOREIGN KEY (away_team_id) REFERENCES teams (id)
                )
            """)
            
            # Tabela de estatísticas de partidas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fixture_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fixture_id INTEGER,
                    team_id INTEGER,
                    shots_on_goal INTEGER,
                    shots_off_goal INTEGER,
                    total_shots INTEGER,
                    blocked_shots INTEGER,
                    shots_inside_box INTEGER,
                    shots_outside_box INTEGER,
                    fouls INTEGER,
                    corner_kicks INTEGER,
                    offsides INTEGER,
                    ball_possession INTEGER,
                    yellow_cards INTEGER,
                    red_cards INTEGER,
                    goalkeeper_saves INTEGER,
                    total_passes INTEGER,
                    passes_accurate INTEGER,
                    passes_percentage INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fixture_id) REFERENCES fixtures (id),
                    FOREIGN KEY (team_id) REFERENCES teams (id)
                )
            """)
            
            # Tabela de estatísticas de times
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS team_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER,
                    league_id INTEGER,
                    season INTEGER,
                    matches_played INTEGER,
                    wins INTEGER,
                    draws INTEGER,
                    losses INTEGER,
                    goals_for INTEGER,
                    goals_against INTEGER,
                    points INTEGER,
                    rank INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams (id),
                    FOREIGN KEY (league_id) REFERENCES leagues (id)
                )
            """)
            
            conn.commit()
            logger.info("Banco de dados inicializado com sucesso")

class FootballAPIClient:
    """Cliente para consumir a API Football API-Sports"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-apisports-key": api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Faz uma requisição para a API"""
        url = f"{API_BASE_URL}/{endpoint}"
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("errors"):
                logger.error(f"Erro na API: {data['errors']}")
                return {}
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para {url}: {e}")
            return {}
    
    def get_fixtures(self, league_id: int, season: int) -> List[Dict]:
        """Obtém todas as partidas de uma liga"""
        params = {"league": league_id, "season": season}
        data = self.make_request("fixtures", params)
        return data.get("response", [])
    
    def get_fixture_statistics(self, fixture_id: int) -> List[Dict]:
        """Obtém estatísticas de uma partida específica"""
        params = {"fixture": fixture_id}
        data = self.make_request("fixtures/statistics", params)
        return data.get("response", [])
    
    def get_team_statistics(self, league_id: int, season: int, team_id: int) -> Dict:
        """Obtém estatísticas de um time específico"""
        params = {"league": league_id, "season": season, "team": team_id}
        data = self.make_request("teams/statistics", params)
        response = data.get("response")
        if response:
            # A API retorna diretamente um objeto, não uma lista
            return response if isinstance(response, dict) else {}
        return {}
    
    def get_standings(self, league_id: int, season: int) -> List[Dict]:
        """Obtém a tabela de classificação da liga"""
        params = {"league": league_id, "season": season}
        data = self.make_request("standings", params)
        if data.get("response"):
            # A API retorna standings como uma lista de arrays, onde cada array contém os times de uma divisão
            standings_data = data["response"][0].get("league", {}).get("standings", [])
            if standings_data and isinstance(standings_data, list):
                # Se standings_data é uma lista de listas, pega a primeira lista (divisão principal)
                if standings_data and isinstance(standings_data[0], list):
                    return standings_data[0]
                # Se standings_data é uma lista direta de times
                elif standings_data and isinstance(standings_data[0], dict):
                    return standings_data
        return []

class FootballDataCollector:
    """Coletor principal de dados de futebol"""
    
    def __init__(self):
        self.db = FootballDatabase(DB_NAME)
        self.api = FootballAPIClient(API_KEY)
    
    def fixture_exists(self, fixture_id: int) -> bool:
        """Verifica se uma partida já existe no banco de dados"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fixtures WHERE id = ?", (fixture_id,))
            return cursor.fetchone()[0] > 0
    
    def fixture_statistics_exist(self, fixture_id: int) -> bool:
        """Verifica se as estatísticas de uma partida já existem"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fixture_statistics WHERE fixture_id = ?", (fixture_id,))
            return cursor.fetchone()[0] > 0
    
    def team_statistics_exist(self, team_id: int, league_id: int, season: int) -> bool:
        """Verifica se as estatísticas de um time já existem"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM team_statistics WHERE team_id = ? AND league_id = ? AND season = ?",
                    (team_id, league_id, season)
                )
                result = cursor.fetchone()
                return result[0] > 0 if result else False
        except Exception as e:
            logger.error(f"❌ Erro ao verificar estatísticas do time {team_id}: {e}")
            return False
    
    def get_processed_fixtures_count(self, league_id: int) -> int:
        """Retorna o número de partidas já processadas para uma liga"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fixtures WHERE league_id = ?", (league_id,))
            return cursor.fetchone()[0]
    
    def get_database_status(self) -> Dict:
        """Retorna o status atual do banco de dados"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            
            # Conta registros em cada tabela
            tables = ['leagues', 'teams', 'fixtures', 'fixture_statistics', 'team_statistics']
            status = {}
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                status[table] = cursor.fetchone()[0]
            
            return status
    
    def log_database_status(self):
        """Exibe o status atual do banco de dados"""
        status = self.get_database_status()
        logger.info("📊 Status atual do banco de dados:")
        logger.info(f"   🏆 Ligas: {status['leagues']}")
        logger.info(f"   👥 Times: {status['teams']}")
        logger.info(f"   ⚽ Partidas: {status['fixtures']}")
        logger.info(f"   📈 Estatísticas de partidas: {status['fixture_statistics']}")
        logger.info(f"   📊 Estatísticas de times: {status['team_statistics']}")
    
    def save_league(self, league_data: Dict) -> int:
        """Salva uma liga no banco de dados"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO leagues (id, name, country, logo, flag, season)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                league_data["id"],
                league_data["name"],
                league_data["country"],
                league_data.get("logo"),
                league_data.get("flag"),
                league_data["season"]
            ))
            
            conn.commit()
            return league_data["id"]
    
    def save_team(self, team_data: Dict, league_id: int) -> int:
        """Salva um time no banco de dados"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO teams (id, name, logo, league_id)
                VALUES (?, ?, ?, ?)
            """, (
                team_data["id"],
                team_data["name"],
                team_data.get("logo"),
                league_id
            ))
            
            conn.commit()
            return team_data["id"]
    
    def save_fixture(self, fixture_data: Dict, league_id: int) -> int:
        """Salva uma partida no banco de dados"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                # Verifica se fixture_data é um dicionário válido
                if not isinstance(fixture_data, dict):
                    logger.warning(f"Dados de partida inválidos: {fixture_data}")
                    return None
                
                fixture = fixture_data.get("fixture", {})
                teams = fixture_data.get("teams", {})
                goals = fixture_data.get("goals", {})
                score = fixture_data.get("score", {})
                
                # Verifica se os dados essenciais estão presentes
                if not fixture.get("id") or not teams.get("home", {}).get("id") or not teams.get("away", {}).get("id"):
                    logger.warning(f"Dados essenciais da partida não encontrados: {fixture_data}")
                    return None
                
                cursor.execute("""
                    INSERT OR REPLACE INTO fixtures (
                        id, league_id, home_team_id, away_team_id, referee,
                        venue_id, venue_name, venue_city, date, timestamp,
                        status, home_goals, away_goals, home_halftime_goals, away_halftime_goals
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fixture["id"],
                    league_id,
                    teams["home"]["id"],
                    teams["away"]["id"],
                    fixture.get("referee"),
                    fixture.get("venue", {}).get("id"),
                    fixture.get("venue", {}).get("name"),
                    fixture.get("venue", {}).get("city"),
                    fixture.get("date"),
                    fixture.get("timestamp"),
                    fixture.get("status", {}).get("long", "Unknown"),
                    goals.get("home", 0),
                    goals.get("away", 0),
                    score.get("halftime", {}).get("home", 0),
                    score.get("halftime", {}).get("away", 0)
                ))
                
                conn.commit()
                logger.debug(f"Partida salva: ID {fixture['id']}")
                return fixture["id"]
                
        except Exception as e:
            logger.error(f"Erro ao salvar partida: {e}")
            logger.error(f"Dados recebidos: {fixture_data}")
            return None
    
    def save_fixture_statistics(self, fixture_id: int, stats_data: List[Dict]):
        """Salva estatísticas de uma partida"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                for stat in stats_data:
                    # Verifica se stat é um dicionário válido
                    if not isinstance(stat, dict):
                        logger.warning(f"Dados de estatísticas inválidos: {stat}")
                        continue
                    
                    team_id = stat.get("team", {}).get("id")
                    if not team_id:
                        logger.warning("ID do time não encontrado nas estatísticas")
                        continue
                    
                    statistics = stat.get("statistics", {})
                    if not isinstance(statistics, dict):
                        # A API pode retornar estatísticas como lista de dicionários
                        if isinstance(statistics, list):
                            # Converte lista de estatísticas para dicionário
                            stats_dict = {}
                            for stat_item in statistics:
                                if isinstance(stat_item, dict) and 'type' in stat_item and 'value' in stat_item:
                                    stats_dict[stat_item['type']] = stat_item['value']
                            statistics = stats_dict
                        else:
                            logger.warning(f"Estatísticas inválidas para time {team_id}: {statistics}")
                            continue
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO fixture_statistics (
                            fixture_id, team_id, shots_on_goal, shots_off_goal, total_shots,
                            blocked_shots, shots_inside_box, shots_outside_box, fouls,
                            corner_kicks, offsides, ball_possession, yellow_cards,
                            red_cards, goalkeeper_saves, total_passes, passes_accurate,
                            passes_percentage
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        fixture_id,
                        team_id,
                        statistics.get("Shots on Goal", 0),
                        statistics.get("Shots off Goal", 0),
                        statistics.get("Total Shots", 0),
                        statistics.get("Blocked Shots", 0),
                        statistics.get("Shots insidebox", 0),
                        statistics.get("Shots outsidebox", 0),
                        statistics.get("Fouls", 0),
                        statistics.get("Corner Kicks", 0),
                        statistics.get("Offsides", 0),
                        statistics.get("Ball Possession", 0),
                        statistics.get("Yellow Cards", 0),
                        statistics.get("Red Cards", 0),
                        statistics.get("Goalkeeper Saves", 0),
                        statistics.get("Total passes", 0),
                        statistics.get("Passes accurate", 0),
                        statistics.get("Passes %", 0)
                    ))
                
                conn.commit()
                logger.debug(f"Estatísticas salvas para partida ID: {fixture_id}")
                
        except Exception as e:
            logger.error(f"Erro ao salvar estatísticas da partida {fixture_id}: {e}")
            logger.error(f"Dados recebidos: {stats_data}")
    
    def save_team_statistics(self, team_stats: Dict, league_id: int):
        """Salva estatísticas de um time usando estrutura correta da API"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                # Verifica se team_stats é um dicionário válido
                if not isinstance(team_stats, dict):
                    logger.warning(f"Dados de estatísticas inválidos para time: {team_stats}")
                    return
                
                team_info = team_stats.get("team", {})
                team_id = team_info.get("id")
                if not team_id:
                    logger.warning("ID do time não encontrado")
                    return
                
                league_info = team_stats.get("league", {})
                fixtures = team_stats.get("fixtures", {})
                goals = team_stats.get("goals", {})
                
                # Extrai dados da estrutura correta da API
                matches_played = fixtures.get("played", {}).get("total", 0)
                wins = fixtures.get("wins", {}).get("total", 0)
                draws = fixtures.get("draws", {}).get("total", 0)
                losses = fixtures.get("loses", {}).get("total", 0)
                
                goals_for = goals.get("for", {}).get("total", {}).get("total", 0)
                goals_against = goals.get("against", {}).get("total", {}).get("total", 0)
                
                points = wins * 3 + draws
                rank = 0  # Será obtido da tabela de standings
                season = league_info.get("season", 2025)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO team_statistics (
                        team_id, league_id, season, matches_played, wins, draws, losses,
                        goals_for, goals_against, points, rank
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    team_id,
                    league_id,
                    season,
                    matches_played,
                    wins,
                    draws,
                    losses,
                    goals_for,
                    goals_against,
                    points,
                    rank
                ))
                
                conn.commit()
                logger.debug(f"📈 Estatísticas salvas para time {team_info.get('name', 'N/A')} (ID: {team_id})")
                
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estatísticas do time: {e}")
            logger.error(f"🔍 Dados recebidos: {team_stats}")
    
    def collect_league_data(self, league_config: LeagueConfig):
        """Coleta todos os dados de uma liga"""
        logger.info(f"🏆 Iniciando coleta da liga: {league_config.name} (ID: {league_config.id})")
        
        # Verifica dados já existentes
        existing_fixtures = self.get_processed_fixtures_count(league_config.id)
        logger.info(f"📊 Partidas já processadas: {existing_fixtures}")
        
        # Salva a liga
        league_data = {
            "id": league_config.id,
            "name": league_config.name,
            "country": league_config.country,
            "season": league_config.season
        }
        self.save_league(league_data)
        logger.info(f"✅ Liga {league_config.name} salva no banco")
        
        # Obtém todas as partidas
        fixtures = self.api.get_fixtures(league_config.id, league_config.season)
        logger.info(f"📋 Encontradas {len(fixtures)} partidas na API")
        
        teams_processed = set()
        fixtures_processed = 0
        fixtures_skipped = 0
        stats_processed = 0
        stats_skipped = 0
        
        for i, fixture in enumerate(fixtures, 1):
            fixture_id = fixture.get("fixture", {}).get("id")
            home_team = fixture.get("teams", {}).get("home", {})
            away_team = fixture.get("teams", {}).get("away", {})
            
            # Log de progresso a cada 50 partidas
            if i % 50 == 0:
                logger.info(f"🔄 Progresso: {i}/{len(fixtures)} partidas processadas")
            
            # Verifica se a partida já existe
            if fixture_id and self.fixture_exists(fixture_id):
                logger.debug(f"⏭️  Partida {fixture_id} já existe, pulando...")
                fixtures_skipped += 1
                continue
            
            # Salva os times se ainda não foram processados
            if home_team.get("id") and home_team["id"] not in teams_processed:
                self.save_team(home_team, league_config.id)
                teams_processed.add(home_team["id"])
                logger.debug(f"✅ Time salvo: {home_team.get('name', 'N/A')}")
            
            if away_team.get("id") and away_team["id"] not in teams_processed:
                self.save_team(away_team, league_config.id)
                teams_processed.add(away_team["id"])
                logger.debug(f"✅ Time salvo: {away_team.get('name', 'N/A')}")
            
            # Salva a partida
            saved_fixture_id = self.save_fixture(fixture, league_config.id)
            
            if saved_fixture_id:
                fixtures_processed += 1
                logger.debug(f"✅ Partida salva: {saved_fixture_id} - {home_team.get('name', 'N/A')} vs {away_team.get('name', 'N/A')}")
                
                # Verifica se as estatísticas já existem
                if not self.fixture_statistics_exist(saved_fixture_id):
                    fixture_stats = self.api.get_fixture_statistics(saved_fixture_id)
                    if fixture_stats:
                            self.save_fixture_statistics(saved_fixture_id, fixture_stats)
                            stats_processed += 1
                            logger.debug(f"📊 Estatísticas salvas para partida {saved_fixture_id}")
                    else:
                        logger.debug(f"⚠️  Nenhuma estatística encontrada para partida {saved_fixture_id}")
                else:
                    stats_skipped += 1
                    logger.debug(f"⏭️  Estatísticas da partida {saved_fixture_id} já existem")
            else:
                logger.warning(f"❌ Falha ao salvar partida: {home_team.get('name', 'N/A')} vs {away_team.get('name', 'N/A')}")
            
            # Aguarda para não sobrecarregar a API
            time.sleep(0.1)
        
        # Obtém estatísticas de todos os times
        logger.info(f"👥 Coletando estatísticas de {len(teams_processed)} times")
        team_stats_processed = 0
        team_stats_skipped = 0
        
        # Primeiro, obtém a tabela de classificação completa
        logger.info(f"📊 Obtendo tabela de classificação da {league_config.name}")
        standings = self.api.get_standings(league_config.id, league_config.season)
        if standings:
            logger.info(f"✅ Tabela de classificação obtida com {len(standings)} times")
            logger.debug(f"📋 Estrutura dos dados: {type(standings)} - Primeiro item: {type(standings[0]) if standings else 'N/A'}")
            
            # Salva estatísticas de todos os times da tabela
            for i, team_standing in enumerate(standings):
                try:
                    if not isinstance(team_standing, dict):
                        logger.warning(f"⚠️  Dados de time inválidos na posição {i}: {team_standing}")
                        continue
                        
                    team_info = team_standing.get("team", {})
                    team_id = team_info.get("id")
                    team_name = team_info.get("name", "N/A")
                    
                    if team_id:
                        logger.debug(f"🔄 Processando time {i+1}/{len(standings)}: {team_name} (ID: {team_id})")
                        
                        # Verifica se as estatísticas do time já existem
                        if not self.team_statistics_exist(team_id, league_config.id, league_config.season):
                            team_stats = self.api.get_team_statistics(league_config.id, league_config.season, team_id)
                            if team_stats:
                                self.save_team_statistics(team_stats, league_config.id)
                                team_stats_processed += 1
                                logger.debug(f"📈 Estatísticas salvas para time {team_id} ({team_name})")
                            else:
                                logger.debug(f"⚠️  Nenhuma estatística encontrada para time {team_id} ({team_name})")
                        else:
                            team_stats_skipped += 1
                            logger.debug(f"⏭️  Estatísticas do time {team_id} ({team_name}) já existem")
                        
                        time.sleep(0.1)
                    else:
                        logger.warning(f"⚠️  ID do time não encontrado na posição {i}: {team_standing}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar time na posição {i}: {e}")
                    logger.error(f"🔍 Tipo do erro: {type(e).__name__}")
                    logger.error(f"🔍 Detalhes do erro: {str(e)}")
                    import traceback
                    logger.error(f"🔍 Traceback: {traceback.format_exc()}")
                    continue
        else:
            logger.warning(f"❌ Não foi possível obter a tabela de classificação da {league_config.name}")
        
        # Também coleta estatísticas dos times que participaram das partidas mas podem não estar na tabela
        for team_id in teams_processed:
            # Verifica se as estatísticas do time já existem
            if not self.team_statistics_exist(team_id, league_config.id, league_config.season):
                team_stats = self.api.get_team_statistics(league_config.id, league_config.season, team_id)
                if team_stats:
                    self.save_team_statistics(team_stats, league_config.id)
                    team_stats_processed += 1
                    logger.debug(f"📈 Estatísticas salvas para time {team_id}")
                else:
                    logger.debug(f"⚠️  Nenhuma estatística encontrada para time {team_id}")
            else:
                team_stats_skipped += 1
                logger.debug(f"⏭️  Estatísticas do time {team_id} já existem")
            
            time.sleep(0.1)
        
        # Resumo final
        logger.info(f"🎯 Resumo da coleta - {league_config.name}:")
        logger.info(f"   📋 Partidas: {fixtures_processed} novas, {fixtures_skipped} puladas")
        logger.info(f"   📊 Estatísticas de partidas: {stats_processed} novas, {stats_skipped} puladas")
        logger.info(f"   👥 Times processados: {len(teams_processed)}")
        logger.info(f"   📈 Estatísticas de times: {team_stats_processed} novas, {team_stats_skipped} puladas")
        logger.info(f"✅ Dados da liga {league_config.name} coletados com sucesso")
    
    def collect_all_data(self):
        """Coleta dados de todas as ligas configuradas"""
        start_time = time.time()
        logger.info("🚀 Iniciando coleta de dados de todas as ligas")
        logger.info(f"📋 Total de ligas configuradas: {len(LEAGUES)}")
        
        # Exibe status inicial do banco
        self.log_database_status()
        
        successful_leagues = 0
        failed_leagues = 0
        
        for i, league_config in enumerate(LEAGUES, 1):
            logger.info(f"🔄 Processando liga {i}/{len(LEAGUES)}: {league_config.name}")
            
            try:
                self.collect_league_data(league_config)
                successful_leagues += 1
                logger.info(f"✅ Liga {league_config.name} processada com sucesso")
            except Exception as e:
                failed_leagues += 1
                logger.error(f"❌ Erro ao processar liga {league_config.name}: {e}")
                logger.error(f"🔍 Detalhes do erro: {type(e).__name__}: {str(e)}")
            
            # Aguarda entre ligas
            if i < len(LEAGUES):
                logger.info("⏳ Aguardando 1 segundo antes da próxima liga...")
            time.sleep(1)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info("🎯 Resumo final da coleta:")
        logger.info(f"   ✅ Ligas processadas com sucesso: {successful_leagues}")
        logger.info(f"   ❌ Ligas com erro: {failed_leagues}")
        logger.info(f"   ⏱️  Tempo total de execução: {duration:.2f} segundos")
        logger.info(f"   📊 Taxa de sucesso: {(successful_leagues/len(LEAGUES)*100):.1f}%")
        
        # Exibe status final do banco
        logger.info("📊 Status final do banco de dados:")
        self.log_database_status()
        
        logger.info("🏁 Coleta de dados concluída")

def salvar_em_github(json_data, filename):
    """Salva dados no GitHub via API REST"""
    if not GITHUB_TOKEN:
        return
    
    try:
        headers = {
            'Authorization': f'Bearer {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json'
        }
        
        content = json.dumps(json_data, indent=2, ensure_ascii=False)
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{filename}"
        
        # Verifica se arquivo existe
        response = requests.get(api_url, headers=headers)
        
        data = {
            'message': f'Atualiza dados: {filename}',
            'content': content_b64,
            'branch': BRANCH
        }
        
        if response.status_code == 200:
            data['sha'] = response.json().get('sha', '')
        
        # Upload
        response = requests.put(api_url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ {filename} enviado para GitHub")
        else:
            logger.error(f"❌ Erro GitHub: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Erro GitHub: {e}")

def calcular_estatisticas_complementares(league_id: int) -> List[Dict]:
    """Calcula estatísticas complementares para uma liga usando dados da API"""
    try:
        # Obtém dados da API de standings
        api_client = FootballAPIClient(API_KEY)
        standings = api_client.get_standings(league_id, 2025)
        
        if not standings:
            logger.warning(f"Nenhuma tabela de classificação encontrada para liga {league_id}")
            return []
        
        result = []
        
        for team_standing in standings:
            # Verifica se team_standing é um dicionário válido
            if not isinstance(team_standing, dict):
                logger.warning(f"Dados de time inválidos: {team_standing}")
                continue
                
            team_info = team_standing.get("team", {})
            all_stats = team_standing.get("all", {})
            home_stats = team_standing.get("home", {})
            away_stats = team_standing.get("away", {})
            goals_stats = team_standing.get("goals", {})
            
            team_id = team_info.get("id")
            team_name = team_info.get("name")
            team_logo = team_info.get("logo")
            
            # Dados básicos da tabela
            rank = team_standing.get("rank", 0)
            points = team_standing.get("points", 0)
            goals_diff = team_standing.get("goalsDiff", 0)
            group = team_standing.get("group", "")
            form = team_standing.get("form", "")[::-1]  # Inverte a string (VFEV -> VEFV)
            status = team_standing.get("status", "")
            description = team_standing.get("description")
            update = team_standing.get("update", "")
            
            # Inicializa form_home e form_visitor
            form_home = ""
            form_visitor = ""
            
            # Inicializa estatísticas
            btts_matches = 0
            btts_home_matches = 0
            btts_away_matches = 0
            avg_corners_per_game = 0
            avg_corners_home_per_game = 0
            avg_corners_away_per_game = 0
            
            # Novas estatísticas
            aproveitamento = 0
            over_2_5_goals = 0
            over_0_5_ht = 0
            over_0_5_ft = 0
            clean_sheets = 0
            matches_played = all_stats.get("played", 0)
            
            if team_id:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    
                    # BTTS Geral
                    btts_query = """
                    SELECT COUNT(*) as btts_matches
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND (f.home_team_id = ? OR f.away_team_id = ?)
                    AND f.home_goals > 0 AND f.away_goals > 0
                    """
                    cursor.execute(btts_query, (league_id, team_id, team_id))
                    btts_result = cursor.fetchone()
                    btts_matches = btts_result[0] if btts_result else 0
                    
                    # BTTS Casa (quando o time é mandante)
                    btts_home_query = """
                    SELECT COUNT(*) as btts_home_matches
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.home_team_id = ?
                    AND f.home_goals > 0 AND f.away_goals > 0
                    """
                    cursor.execute(btts_home_query, (league_id, team_id))
                    btts_home_result = cursor.fetchone()
                    btts_home_matches = btts_home_result[0] if btts_home_result else 0
                    
                    # BTTS Fora (quando o time é visitante)
                    btts_away_query = """
                    SELECT COUNT(*) as btts_away_matches
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.away_team_id = ?
                    AND f.home_goals > 0 AND f.away_goals > 0
                    """
                    cursor.execute(btts_away_query, (league_id, team_id))
                    btts_away_result = cursor.fetchone()
                    btts_away_matches = btts_away_result[0] if btts_away_result else 0
                    
                    # Aproveitamento (Pontos ganhos / Pontos disputados)
                    if matches_played > 0:
                        max_points = matches_played * 3
                        aproveitamento = round((points / max_points) * 100, 1)
                    
                    # +2.5 gols (Jogos com 3 ou mais gols) - GERAL
                    over_2_5_query = """
                    SELECT COUNT(*) as over_2_5_goals
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND (f.home_team_id = ? OR f.away_team_id = ?)
                    AND (f.home_goals + f.away_goals) >= 3
                    """
                    cursor.execute(over_2_5_query, (league_id, team_id, team_id))
                    over_2_5_result = cursor.fetchone()
                    over_2_5_goals = over_2_5_result[0] if over_2_5_result else 0
                    
                    # +2.5 gols (Jogos com 3 ou mais gols) - CASA
                    over_2_5_home_query = """
                    SELECT COUNT(*) as over_2_5_goals_home
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.home_team_id = ?
                    AND (f.home_goals + f.away_goals) >= 3
                    """
                    cursor.execute(over_2_5_home_query, (league_id, team_id))
                    over_2_5_home_result = cursor.fetchone()
                    over_2_5_goals_home = over_2_5_home_result[0] if over_2_5_home_result else 0
                    
                    # +2.5 gols (Jogos com 3 ou mais gols) - FORA
                    over_2_5_away_query = """
                    SELECT COUNT(*) as over_2_5_goals_away
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.away_team_id = ?
                    AND (f.home_goals + f.away_goals) >= 3
                    """
                    cursor.execute(over_2_5_away_query, (league_id, team_id))
                    over_2_5_away_result = cursor.fetchone()
                    over_2_5_goals_away = over_2_5_away_result[0] if over_2_5_away_result else 0
                    
                    # +0.5 gol HT (Jogos em que o time marcou no 1º Tempo) - GERAL
                    over_0_5_ht_query = """
                    SELECT COUNT(*) as over_0_5_ht
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND (
                        (f.home_team_id = ? AND f.home_halftime_goals > 0) OR 
                        (f.away_team_id = ? AND f.away_halftime_goals > 0)
                    )
                    """
                    cursor.execute(over_0_5_ht_query, (league_id, team_id, team_id))
                    over_0_5_ht_result = cursor.fetchone()
                    over_0_5_ht = over_0_5_ht_result[0] if over_0_5_ht_result else 0
                    
                    # +0.5 gol HT (Jogos em que o time marcou no 1º Tempo) - CASA
                    over_0_5_ht_home_query = """
                    SELECT COUNT(*) as over_0_5_ht_home
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.home_team_id = ? AND f.home_halftime_goals > 0
                    """
                    cursor.execute(over_0_5_ht_home_query, (league_id, team_id))
                    over_0_5_ht_home_result = cursor.fetchone()
                    over_0_5_ht_home = over_0_5_ht_home_result[0] if over_0_5_ht_home_result else 0
                    
                    # +0.5 gol HT (Jogos em que o time marcou no 1º Tempo) - FORA
                    over_0_5_ht_away_query = """
                    SELECT COUNT(*) as over_0_5_ht_away
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.away_team_id = ? AND f.away_halftime_goals > 0
                    """
                    cursor.execute(over_0_5_ht_away_query, (league_id, team_id))
                    over_0_5_ht_away_result = cursor.fetchone()
                    over_0_5_ht_away = over_0_5_ht_away_result[0] if over_0_5_ht_away_result else 0
                    
                    # +0.5 gol FT (Jogos em que o time marcou no 2º Tempo) - GERAL
                    over_0_5_ft_query = """
                    SELECT COUNT(*) as over_0_5_ft
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND (
                        (f.home_team_id = ? AND (f.home_goals - f.home_halftime_goals) > 0) OR 
                        (f.away_team_id = ? AND (f.away_goals - f.away_halftime_goals) > 0)
                    )
                    """
                    cursor.execute(over_0_5_ft_query, (league_id, team_id, team_id))
                    over_0_5_ft_result = cursor.fetchone()
                    over_0_5_ft = over_0_5_ft_result[0] if over_0_5_ft_result else 0
                    
                    # +0.5 gol FT (Jogos em que o time marcou no 2º Tempo) - CASA
                    over_0_5_ft_home_query = """
                    SELECT COUNT(*) as over_0_5_ft_home
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.home_team_id = ? AND (f.home_goals - f.home_halftime_goals) > 0
                    """
                    cursor.execute(over_0_5_ft_home_query, (league_id, team_id))
                    over_0_5_ft_home_result = cursor.fetchone()
                    over_0_5_ft_home = over_0_5_ft_home_result[0] if over_0_5_ft_home_result else 0
                    
                    # +0.5 gol FT (Jogos em que o time marcou no 2º Tempo) - FORA
                    over_0_5_ft_away_query = """
                    SELECT COUNT(*) as over_0_5_ft_away
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.away_team_id = ? AND (f.away_goals - f.away_halftime_goals) > 0
                    """
                    cursor.execute(over_0_5_ft_away_query, (league_id, team_id))
                    over_0_5_ft_away_result = cursor.fetchone()
                    over_0_5_ft_away = over_0_5_ft_away_result[0] if over_0_5_ft_away_result else 0
                    
                    # Sem sofrer gol (Clean sheets) - GERAL
                    clean_sheets_query = """
                    SELECT COUNT(*) as clean_sheets
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND (
                        (f.home_team_id = ? AND f.away_goals = 0) OR 
                        (f.away_team_id = ? AND f.home_goals = 0)
                    )
                    """
                    cursor.execute(clean_sheets_query, (league_id, team_id, team_id))
                    clean_sheets_result = cursor.fetchone()
                    clean_sheets = clean_sheets_result[0] if clean_sheets_result else 0
                    
                    # Sem sofrer gol (Clean sheets) - CASA
                    clean_sheets_home_query = """
                    SELECT COUNT(*) as clean_sheets_home
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.home_team_id = ? AND f.away_goals = 0
                    """
                    cursor.execute(clean_sheets_home_query, (league_id, team_id))
                    clean_sheets_home_result = cursor.fetchone()
                    clean_sheets_home = clean_sheets_home_result[0] if clean_sheets_home_result else 0
                    
                    # Sem sofrer gol (Clean sheets) - FORA
                    clean_sheets_away_query = """
                    SELECT COUNT(*) as clean_sheets_away
                    FROM fixtures f
                    WHERE f.league_id = ? 
                    AND f.away_team_id = ? AND f.home_goals = 0
                    """
                    cursor.execute(clean_sheets_away_query, (league_id, team_id))
                    clean_sheets_away_result = cursor.fetchone()
                    clean_sheets_away = clean_sheets_away_result[0] if clean_sheets_away_result else 0
                    
                    try:
                        # Escanteios Gerais (produzidos pelo time)
                        corners_query = """
                        SELECT 
                            COALESCE(SUM(fs.corner_kicks), 0) as total_corners,
                            COUNT(DISTINCT fs.fixture_id) as total_matches
                        FROM fixture_statistics fs
                        JOIN fixtures f ON fs.fixture_id = f.id
                        WHERE f.league_id = ? AND fs.team_id = ?
                        """
                        cursor.execute(corners_query, (league_id, team_id))
                        corners_result = cursor.fetchone()
                        if corners_result and corners_result[1] > 0:
                            avg_corners_per_game = round(corners_result[0] / corners_result[1], 2)
                        
                        # Escanteios Casa (produzidos pelo time quando mandante)
                        corners_home_query = """
                        SELECT 
                            COALESCE(SUM(fs.corner_kicks), 0) as total_corners,
                            COUNT(DISTINCT fs.fixture_id) as total_matches
                        FROM fixture_statistics fs
                        JOIN fixtures f ON fs.fixture_id = f.id
                        WHERE f.league_id = ? AND fs.team_id = ? AND f.home_team_id = ?
                        """
                        cursor.execute(corners_home_query, (league_id, team_id, team_id))
                        corners_home_result = cursor.fetchone()
                        if corners_home_result and corners_home_result[1] > 0:
                            avg_corners_home_per_game = round(corners_home_result[0] / corners_home_result[1], 2)
                        
                        # Escanteios Fora (produzidos pelo time quando visitante)
                        corners_away_query = """
                        SELECT 
                            COALESCE(SUM(fs.corner_kicks), 0) as total_corners,
                            COUNT(DISTINCT fs.fixture_id) as total_matches
                        FROM fixture_statistics fs
                        JOIN fixtures f ON fs.fixture_id = f.id
                        WHERE f.league_id = ? AND fs.team_id = ? AND f.away_team_id = ?
                        """
                        cursor.execute(corners_away_query, (league_id, team_id, team_id))
                        corners_away_result = cursor.fetchone()
                        if corners_away_result and corners_away_result[1] > 0:
                            avg_corners_away_per_game = round(corners_away_result[0] / corners_away_result[1], 2)
                            
                    except Exception as e:
                        logger.warning(f"Erro ao calcular escanteios para time {team_id}: {e}")
                        avg_corners_per_game = 0
                        avg_corners_home_per_game = 0
                        avg_corners_away_per_game = 0
                    
                    # Calcula form_home e form_visitor baseado nas últimas 5 partidas
                    try:
                        # Form Home - últimas 5 partidas em casa
                        form_home_query = """
                        SELECT 
                            CASE 
                                WHEN f.home_goals > f.away_goals THEN 'W'
                                WHEN f.home_goals = f.away_goals THEN 'D'
                                WHEN f.home_goals < f.away_goals THEN 'L'
                                ELSE NULL
                            END as result
                        FROM fixtures f
                        WHERE f.league_id = ? AND f.home_team_id = ? AND f.status = 'Match Finished'
                        ORDER BY f.timestamp DESC
                        LIMIT 5
                        """
                        cursor.execute(form_home_query, (league_id, team_id))
                        form_home_results = cursor.fetchall()
                        form_home = ''.join([result[0] for result in form_home_results if result[0] is not None])[::-1]
                        
                        # Form Visitor - últimas 5 partidas fora
                        form_visitor_query = """
                        SELECT 
                            CASE 
                                WHEN f.away_goals > f.home_goals THEN 'W'
                                WHEN f.away_goals = f.home_goals THEN 'D'
                                WHEN f.away_goals < f.home_goals THEN 'L'
                                ELSE NULL
                            END as result
                        FROM fixtures f
                        WHERE f.league_id = ? AND f.away_team_id = ? AND f.status = 'Match Finished'
                        ORDER BY f.timestamp DESC
                        LIMIT 5
                        """
                        cursor.execute(form_visitor_query, (league_id, team_id))
                        form_visitor_results = cursor.fetchall()
                        form_visitor = ''.join([result[0] for result in form_visitor_results if result[0] is not None])[::-1]
                        
                        logger.debug(f"📊 Form calculado para {team_name}: Home='{form_home}', Visitor='{form_visitor}'")
                        
                    except Exception as e:
                        logger.warning(f"Erro ao calcular form para time {team_id}: {e}")
                        form_home = ""
                        form_visitor = ""
            
            # Estrutura completa seguindo o padrão do brasileirao.json com estatísticas adicionais
            team_dict = {
                "rank": rank,
                "team": {
                    "id": team_id,
                    "name": team_name,
                    "logo": team_logo
                },
                "points": points,
                "goalsDiff": goals_diff,
                "group": group,
                "form": form,
                "form_home": form_home,
                "form_visitor": form_visitor,
                "status": status,
                "description": description,
                "all": all_stats,
                "home": home_stats,
                "away": away_stats,
                "update": update,
                # BTTS - Both Teams To Score (quantidade de jogos onde ambas marcaram)
                "btts_matches": btts_matches,  # Geral
                "btts_home_matches": btts_home_matches,  # Casa
                "btts_away_matches": btts_away_matches,  # Fora
                # Média de escanteios por jogo (produzidos pelo time)
                "avg_corners_per_game": avg_corners_per_game,  # Geral
                "avg_corners_home_per_game": avg_corners_home_per_game,  # Casa
                "avg_corners_away_per_game": avg_corners_away_per_game,  # Fora
                # Novas estatísticas - GERAL
                "aproveitamento": aproveitamento,  # Aproveitamento em %
                "over_2_5_goals": over_2_5_goals,  # Jogos com 3+ gols
                "over_0_5_ht": over_0_5_ht,  # Jogos com gol no 1º tempo
                "over_0_5_ft": over_0_5_ft,  # Jogos com gol no 2º tempo
                "clean_sheets": clean_sheets,  # Jogos sem sofrer gol
                # Novas estatísticas - CASA
                "over_2_5_goals_home": over_2_5_goals_home,  # Jogos com 3+ gols em casa
                "over_0_5_ht_home": over_0_5_ht_home,  # Jogos com gol no 1º tempo em casa
                "over_0_5_ft_home": over_0_5_ft_home,  # Jogos com gol no 2º tempo em casa
                "clean_sheets_home": clean_sheets_home,  # Jogos sem sofrer gol em casa
                # Novas estatísticas - FORA
                "over_2_5_goals_away": over_2_5_goals_away,  # Jogos com 3+ gols fora
                "over_0_5_ht_away": over_0_5_ht_away,  # Jogos com gol no 1º tempo fora
                "over_0_5_ft_away": over_0_5_ft_away,  # Jogos com gol no 2º tempo fora
                "clean_sheets_away": clean_sheets_away  # Jogos sem sofrer gol fora
            }
            result.append(team_dict)
            
            # Log detalhado para debug
            logger.debug(f"📊 Estatísticas calculadas para {team_name}:")
            logger.debug(f"   - BTTS Geral: {btts_matches}, Casa: {btts_home_matches}, Fora: {btts_away_matches}")
            logger.debug(f"   - Escanteios Geral: {avg_corners_per_game}, Casa: {avg_corners_home_per_game}, Fora: {avg_corners_away_per_game}")
            logger.debug(f"   - Aproveitamento: {aproveitamento}%")
            logger.debug(f"   - +2.5 gols: {over_2_5_goals}, +0.5 HT: {over_0_5_ht}, +0.5 FT: {over_0_5_ft}, Clean sheets: {clean_sheets}")
            logger.debug(f"   - Gols 1ºT Casa: {over_0_5_ht_home}, Gols 1ºT Fora: {over_0_5_ht_away}")
            logger.debug(f"   - Gols 2ºT Casa: {over_0_5_ft_home}, Gols 2ºT Fora: {over_0_5_ft_away}")
        
        logger.info(f"✅ Estatísticas complementares calculadas para {len(result)} times")
        return result
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas complementares para liga {league_id}: {e}")
        return []

def obter_artilharia(league_id: int) -> List[Dict]:
    """Obtém dados de artilharia da liga seguindo o padrão brasileirao.json"""
    try:
        headers = {"x-apisports-key": API_KEY}
        url = f"{API_BASE_URL}/players/topscorers"
        params = {"league": league_id, "season": 2025}
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Verifica se há erros na resposta da API
        if data.get("errors"):
            logger.error(f"Erro na API de artilharia: {data['errors']}")
            return []
        
        artilharia = []
        for item in data.get("response", []):
            try:
                jogador = item.get("player", {})
                estat = item.get("statistics", [{}])[0]
                time_info = estat.get("team", {})
                
                # Obtém a posição do jogador da API (está em statistics[0].games.position)
                jogador_posicao = estat.get("games", {}).get("position", "N/A")
                
                # Verifica se o jogador tem gols
                gols = estat.get("goals", {}).get("total", 0)
                if gols > 0:  # Só inclui jogadores que marcaram gols
                    artilharia.append({
                        "jogador-foto": jogador.get("photo"),
                        "jogador-escudo": time_info.get("logo"),
                        "jogador-nome": jogador.get("name"),
                        "jogador-posicao": jogador_posicao,
                        "jogador-gols": gols
                    })
            except Exception as e:
                logger.warning(f"Erro ao processar jogador na artilharia: {e}")
                continue
        
        # Ordena por número de gols (decrescente)
        artilharia.sort(key=lambda x: x["jogador-gols"], reverse=True)
        
        logger.info(f"Artilharia obtida para liga {league_id}: {len(artilharia)} jogadores")
        return artilharia
    except Exception as e:
        logger.error(f"Erro ao obter artilharia para liga {league_id}: {e}")
        return []

def processar_competicao(league_group):
    """Processa uma competição completa com múltiplas ligas e retorna os dados seguindo o padrão brasileirao.json"""
    logger.info(f"📊 Processando competição: {league_group['id']}")
    
    standings_data = {}
    artilharia_data = {}
    
    # Processa cada liga do grupo
    for league_config in league_group["leagues"]:
        logger.info(f"🔄 Processando liga: {league_config.name}")
        
        # Calcular estatísticas complementares (standings)
        standings = calcular_estatisticas_complementares(league_config.id)
        logger.info(f"📊 Standings processados: {len(standings)} times")
        
        # Obter artilharia
        artilharia = obter_artilharia(league_config.id)
        logger.info(f"⚽ Artilharia processada: {len(artilharia)} jogadores")
        
        # Adiciona aos dados da competição usando a chave da liga
        league_key = league_config.name.lower().replace(' ', '_')
        standings_data[league_key] = standings
        artilharia_data[league_key] = artilharia
    
    # Estrutura final seguindo o padrão esperado pelo frontend
    dados_finais = {
        "standings": standings_data,
        "artilharia": artilharia_data
    }
    
    # Log resumido
    logger.info(f"📋 {league_group['id']}: {len(standings_data)} ligas, {len(artilharia_data)} artilharias")
    
    # Salva no GitHub se configurado
    if GITHUB_TOKEN:
        filename = league_group["output_filename"]
        salvar_em_github(dados_finais, filename)
    
    # Salva localmente
    filename = league_group["output_filename"]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(dados_finais, f, indent=2, ensure_ascii=False)
    

    
    return dados_finais

def main():
    """Função principal"""
    start_time = time.time()
    
    try:
        logger.info("🎯 Iniciando sistema de coleta de dados de futebol")
        logger.info("=" * 60)
        
        # Coletar dados
        logger.info("📊 FASE 1: Coleta de dados das ligas")
        collector = FootballDataCollector()
        collector.collect_all_data()
        logger.info("✅ FASE 1 concluída: Coleta de dados finalizada!")
        
        # Processar competições e salvar no GitHub
        logger.info("🌐 FASE 2: Processamento e salvamento no GitHub")
        logger.info(f"📋 Processando {len(LEAGUE_GROUPS)} competições...")
        
        successful_processing = 0
        failed_processing = 0
        
        for i, league_group in enumerate(LEAGUE_GROUPS, 1):
            logger.info(f"🔄 Processando competição {i}/{len(LEAGUE_GROUPS)}: {league_group['id']}")
            
            try:
                dados = processar_competicao(league_group)
                successful_processing += 1
                logger.info(f"✅ {league_group['id']} processada e salva no GitHub")
                
                # Log de detalhes dos dados processados
                if dados:
                    standings_count = len(dados.get("standings", {}))
                    artilharia_count = len(dados.get("artilharia", {}))
                    logger.info(f"   📊 {standings_count} ligas na tabela")
                    logger.info(f"   ⚽ {artilharia_count} ligas na artilharia")
                
                if i < len(LEAGUE_GROUPS):
                    logger.info("⏳ Aguardando 1 segundo antes da próxima competição...")
                    time.sleep(1)
                    
            except Exception as e:
                failed_processing += 1
                logger.error(f"❌ Erro ao processar {league_group['id']}: {e}")
                logger.error(f"🔍 Detalhes do erro: {type(e).__name__}: {str(e)}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("🎯 RESUMO FINAL DO PROCESSAMENTO:")
        logger.info(f"   ✅ Competições processadas com sucesso: {successful_processing}")
        logger.info(f"   ❌ Competições com erro: {failed_processing}")
        logger.info(f"   ⏱️  Tempo total de execução: {duration:.2f} segundos")
        logger.info(f"   📊 Taxa de sucesso: {(successful_processing/len(LEAGUE_GROUPS)*100):.1f}%")
        logger.info("🎉 Processamento completo com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro crítico no processamento: {e}")
        logger.error(f"🔍 Detalhes do erro: {type(e).__name__}: {str(e)}")
        raise

if __name__ == "__main__":
    main()

