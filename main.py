import os
import requests
import sqlite3
import json
import time
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configurações da API FootyStats
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("FOOTYSTATS_API_KEY")

if not API_KEY:
    raise ValueError("FOOTYSTATS_API_KEY não configurada no arquivo .env")

# Configurações do banco de dados
DB_NAME = "football_stats.db"

# ⚙️ CONFIGURAÇÕES GIT
GITHUB_USER = os.getenv("GITHUB_USER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BRANCH = "main"

@dataclass
class LeagueConfig:
    """Configuração de uma liga"""
    id: int
    name: str
    country: str
    season_id: int
    season_year: int

# As ligas serão obtidas dinamicamente da API
LEAGUES = []

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
                    image TEXT,
                    season_id INTEGER NOT NULL,
                    season_year INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de times (expandida com campos da API)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER,
                    name TEXT NOT NULL,
                    clean_name TEXT,
                    english_name TEXT,
                    short_hand TEXT,
                    country TEXT,
                    continent TEXT,
                    founded TEXT,
                    image TEXT,
                    flag_element TEXT,
                    season TEXT,
                    season_clean TEXT,
                    url TEXT,
                    table_position INTEGER,
                    performance_rank INTEGER,
                    risk INTEGER,
                    season_format TEXT,
                    competition_id INTEGER,
                    full_name TEXT,
                    alt_names TEXT,
                    official_sites TEXT,
                    league_id INTEGER,
                    season_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (league_id) REFERENCES leagues (id),
                    PRIMARY KEY(id, league_id, season_id)
                )
            """)
            
            # Tabela de partidas (expandida com campos da API)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fixtures (
                    id INTEGER PRIMARY KEY,
                    league_id INTEGER,
                    season_id INTEGER,
                    home_team_id INTEGER,
                    away_team_id INTEGER,
                    home_team_name TEXT,
                    away_team_name TEXT,
                    home_team_url TEXT,
                    away_team_url TEXT,
                    home_team_image TEXT,
                    away_team_image TEXT,
                    season TEXT,
                    status TEXT,
                    round_id INTEGER,
                    game_week INTEGER,
                    revised_game_week INTEGER,
                    home_goals TEXT,
                    away_goals TEXT,
                    home_goal_count INTEGER,
                    away_goal_count INTEGER,
                    total_goal_count INTEGER,
                    home_corners INTEGER,
                    away_corners INTEGER,
                    total_corner_count INTEGER,
                    home_offsides INTEGER,
                    away_offsides INTEGER,
                    home_yellow_cards INTEGER,
                    away_yellow_cards INTEGER,
                    home_red_cards INTEGER,
                    away_red_cards INTEGER,
                    home_shots_on_target INTEGER,
                    away_shots_on_target INTEGER,
                    home_shots_off_target INTEGER,
                    away_shots_off_target INTEGER,
                    home_shots INTEGER,
                    away_shots INTEGER,
                    home_fouls INTEGER,
                    away_fouls INTEGER,
                    home_possession INTEGER,
                    away_possession INTEGER,
                    referee_id INTEGER,
                    coach_a_id INTEGER,
                    coach_b_id INTEGER,
                    stadium_name TEXT,
                    stadium_location TEXT,
                    home_cards_num INTEGER,
                    away_cards_num INTEGER,
                    home_halftime_goals INTEGER,
                    away_halftime_goals INTEGER,
                    goals_2hg_home INTEGER,
                    goals_2hg_away INTEGER,
                    goal_count_2hg INTEGER,
                    ht_goal_count INTEGER,
                    date_unix INTEGER,
                    winning_team INTEGER,
                    no_home_away INTEGER,
                    btts_potential INTEGER,
                    btts_fhg_potential INTEGER,
                    btts_2hg_potential INTEGER,
                    goal_timing_disabled INTEGER,
                    attendance INTEGER,
                    corner_timings_recorded INTEGER,
                    card_timings_recorded INTEGER,
                    home_fh_corners INTEGER,
                    away_fh_corners INTEGER,
                    home_2h_corners INTEGER,
                    away_2h_corners INTEGER,
                    corner_fh_count INTEGER,
                    corner_2h_count INTEGER,
                    home_fh_cards INTEGER,
                    away_fh_cards INTEGER,
                    home_2h_cards INTEGER,
                    away_2h_cards INTEGER,
                    total_fh_cards INTEGER,
                    total_2h_cards INTEGER,
                    attacks_recorded INTEGER,
                    home_dangerous_attacks INTEGER,
                    away_dangerous_attacks INTEGER,
                    home_attacks INTEGER,
                    away_attacks INTEGER,
                    home_xg REAL,
                    away_xg REAL,
                    total_xg REAL,
                    home_penalties_won INTEGER,
                    away_penalties_won INTEGER,
                    home_penalty_goals INTEGER,
                    away_penalty_goals INTEGER,
                    home_penalty_missed INTEGER,
                    away_penalty_missed INTEGER,
                    pens_recorded INTEGER,
                    goal_timings_recorded INTEGER,
                    home_0_10_min_goals INTEGER,
                    away_0_10_min_goals INTEGER,
                    home_corners_0_10_min INTEGER,
                    away_corners_0_10_min INTEGER,
                    home_cards_0_10_min INTEGER,
                    away_cards_0_10_min INTEGER,
                    throwins_recorded INTEGER,
                    home_throwins INTEGER,
                    away_throwins INTEGER,
                    freekicks_recorded INTEGER,
                    home_freekicks INTEGER,
                    away_freekicks INTEGER,
                    goalkicks_recorded INTEGER,
                    home_goalkicks INTEGER,
                    away_goalkicks INTEGER,
                    home_ppg REAL,
                    away_ppg REAL,
                    pre_match_home_ppg REAL,
                    pre_match_away_ppg REAL,
                    pre_match_home_overall_ppg REAL,
                    pre_match_away_overall_ppg REAL,
                    match_url TEXT,
                    competition_id INTEGER,
                    matches_completed_minimum INTEGER,
                    over05 BOOLEAN,
                    over15 BOOLEAN,
                    over25 BOOLEAN,
                    over35 BOOLEAN,
                    over45 BOOLEAN,
                    over55 BOOLEAN,
                    btts BOOLEAN,
                    home_goals_timings TEXT,
                    away_goals_timings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (league_id) REFERENCES leagues (id),
                    FOREIGN KEY (home_team_id) REFERENCES teams (id),
                    FOREIGN KEY (away_team_id) REFERENCES teams (id)
                )
            """)
            
            
            # Tabela de estatísticas de times
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS team_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER,
                    league_id INTEGER,
                    season_id INTEGER,
                    season_year INTEGER,
                    matches_played INTEGER,
                    wins INTEGER,
                    draws INTEGER,
                    losses INTEGER,
                    goals_for INTEGER,
                    goals_against INTEGER,
                    points INTEGER,
                    rank INTEGER,
                    position INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams (id),
                    FOREIGN KEY (league_id) REFERENCES leagues (id),
                    UNIQUE(team_id, league_id, season_id)
                )
            """)
            
        # Tabela de jogadores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                team_id INTEGER,
                team_name TEXT,
                position TEXT,
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                matches_played INTEGER DEFAULT 0,
                league_id INTEGER,
                season_id INTEGER,
                age INTEGER,
                height INTEGER,
                weight INTEGER,
                url TEXT,
                minutes_played INTEGER DEFAULT 0,
                clean_sheets INTEGER DEFAULT 0,
                yellow_cards INTEGER DEFAULT 0,
                red_cards INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id),
                FOREIGN KEY (league_id) REFERENCES leagues (id),
                UNIQUE(name, team_id, season_id)
            )
        """)
            
        # Tabela de jogadores por partida
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER,
                    player_name TEXT,
                    team_id INTEGER,
                    goals INTEGER DEFAULT 0,
                    assists INTEGER DEFAULT 0,
                    position TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_id) REFERENCES fixtures (id),
                    FOREIGN KEY (team_id) REFERENCES teams (id),
                    UNIQUE(match_id, player_name, team_id)
                )
            """)
            
        conn.commit()
        logger.info("Banco de dados inicializado com sucesso")

class FootyStatsAPIClient:
    """Cliente para consumir a API FootyStats"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
    
    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        if params is None:
            params = {}
        
        params['key'] = self.api_key
        url = f"{API_BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para {url}: {e}")
            return {}
    
    def get_available_leagues(self) -> List[Dict]:
        """Obtém todas as ligas disponíveis"""
        params = {"chosen_leagues_only": "true"}
        data = self.make_request("league-list", params)
        return data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    
    def get_league_matches(self, season_id: int) -> List[Dict]:
        """Obtém todas as partidas de uma temporada"""
        params = {"season": season_id, "league_id": season_id}
        data = self.make_request("league-matches", params)
        return data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    
    def get_league_teams(self, season_id: int) -> List[Dict]:
        """Obtém todos os times de uma temporada"""
        params = {"season": season_id, "league_id": season_id}
        data = self.make_request("league-teams", params)
        return data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    
    def get_league_players(self, season_id: int) -> List[Dict]:
        """Obtém TODOS os jogadores da liga com paginação automática"""
        all_players = []
        page = 1
        
        while True:
            params = {"season": season_id, "league_id": season_id, "page": page}
            data = self.make_request("league-players", params)
            
            if not data or not isinstance(data, dict):
                break
                
            players = data.get("data", [])
            if not players:
                break
                
            all_players.extend(players)
            
            # Verifica se há mais páginas
            pager = data.get("pager", {})
            current_page = pager.get("current_page", page)
            max_page = pager.get("max_page", 1)
            
            if current_page % 5 == 0 or current_page == max_page:
                logger.info(f"📄 Página {current_page}/{max_page}: {len(players)} jogadores coletados")
            
            if current_page >= max_page:
                break
                
            page += 1
            
            # Delay reduzido para otimização
            time.sleep(0.01)
        
        total_results = data.get("pager", {}).get("total_results", len(all_players))
        logger.info(f"✅ Total de jogadores coletados: {len(all_players)}/{total_results}")
        
        return all_players

class FootballDataCollector:
    """Coletor principal de dados de futebol"""
    
    def __init__(self):
        self.db = FootballDatabase(DB_NAME)
        self.api = FootyStatsAPIClient(API_KEY)
        self.leagues = []
    
    def get_current_year(self) -> int:
        """Retorna o ano atual"""
        return datetime.now().year
    
    def get_latest_season(self, seasons: List[Dict]) -> Dict:
        """Retorna a temporada mais recente disponível"""
        if not seasons:
            return None
        
        # Ordena por ano (mais recente primeiro)
        sorted_seasons = sorted(seasons, key=lambda x: x.get("year", 0), reverse=True)
        return sorted_seasons[0]
    
    def get_league_id_from_database(self, season_id: int, league_name: str, country: str) -> int:
        """Busca o league_id correto no banco de dados baseado no season_id"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                # Busca o league_id que tem mais fixtures para este season_id
                cursor.execute("""
                    SELECT league_id, COUNT(*) as fixture_count
                    FROM fixtures 
                    WHERE season_id = ?
                    GROUP BY league_id
                    ORDER BY fixture_count DESC
                    LIMIT 1
                """, (season_id,))
                
                result = cursor.fetchone()
                if result:
                    league_id = result[0]
                    fixture_count = result[1]
                    logger.info(f"🔍 League ID encontrado para {league_name} (season {season_id}): {league_id} ({fixture_count} fixtures)")
                    return league_id
                else:
                    # Se não encontrar no banco, usa hash como fallback
                    league_id = hash(f"{league_name}_{country}_{season_id}") % 1000000
                    logger.warning(f"⚠️ League ID não encontrado no banco para {league_name}, usando hash: {league_id}")
                    return league_id
                    
        except Exception as e:
            logger.error(f"❌ Erro ao buscar league_id no banco: {e}")
            # Fallback para hash
            league_id = hash(f"{league_name}_{country}_{season_id}") % 1000000
            return league_id
    
    def load_leagues_from_api(self):
        """Carrega as ligas escolhidas da API"""
        logger.info("🔍 Obtendo ligas escolhidas da API FootyStats...")
        
        # Obtém apenas ligas escolhidas
        api_leagues = self.api.get_available_leagues()
        
        if not api_leagues:
            logger.error("❌ Nenhuma liga escolhida encontrada! Configure as ligas na API FootyStats primeiro.")
            return []
        
        logger.info(f"📋 Encontradas {len(api_leagues)} ligas escolhidas na API")
        
        # Mapeia as ligas da API para o formato interno
        for league_data in api_leagues:
            try:
                league_name = league_data.get("name", "")
                country = league_data.get("country", "")
                
                # Pega a temporada mais recente
                seasons = league_data.get("season", [])
                latest_season = self.get_latest_season(seasons)
                
                if not latest_season:
                    logger.warning(f"❌ Nenhuma temporada encontrada para liga: {league_name}")
                    continue
                
                season_id = latest_season.get("id")
                season_year = latest_season.get("year")
                
                if season_id and season_year:
                    # Busca o league_id correto no banco de dados
                    league_id = self.get_league_id_from_database(season_id, league_name, country)
                    
                    league_config = LeagueConfig(
                        id=league_id,
                        name=league_name,
                        country=country,
                        season_id=season_id,
                        season_year=season_year
                    )
                    self.leagues.append(league_config)
                    logger.info(f"✅ Liga adicionada: {league_config.name} (Temporada: {season_year}, ID: {season_id})")
                else:
                    logger.warning(f"❌ Dados de temporada inválidos para liga: {league_name}")
                    
            except Exception as e:
                logger.warning(f"❌ Erro ao processar liga: {league_data} - {e}")
        
        logger.info(f"✅ {len(self.leagues)} ligas carregadas com sucesso")
        return self.leagues
    
    
    def should_update_fixture(self, fixture_id: int, fixture_data: Dict) -> bool:
        """Verifica se uma partida deve ser atualizada baseado no status"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            
            # Busca dados atuais da partida
            cursor.execute("""
                SELECT status, home_goal_count, away_goal_count, created_at 
                FROM fixtures WHERE id = ?
            """, (fixture_id,))
            
            result = cursor.fetchone()
            if not result:
                return True  # Partida não existe, deve ser criada
            
            current_status, current_home_goals, current_away_goals, created_at = result
            new_status = fixture_data.get("status", "")
            new_home_goals = fixture_data.get("home_goal_count", 0)
            new_away_goals = fixture_data.get("away_goal_count", 0)
            
            # Sempre atualiza se:
            # 1. Status mudou (ex: de "scheduled" para "complete")
            # 2. Placar mudou
            # 3. Partida foi criada há mais de 24h e ainda não está completa
            if (current_status != new_status or 
                current_home_goals != new_home_goals or 
                current_away_goals != new_away_goals):
                return True
            
            # Se a partida não está completa e foi criada há mais de 24h, atualiza
            if (new_status not in ["complete", "finished"] and 
                created_at and 
                (time.time() - time.mktime(time.strptime(created_at, "%Y-%m-%d %H:%M:%S"))) > 86400):
                return True
            
            return False
    
    
    
    
    
    
    def save_league(self, league_data: Dict) -> int:
        """Salva uma liga no banco de dados"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO leagues (id, name, country, image, season_id, season_year)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                league_data["id"],
                league_data["name"],
                league_data["country"],
                league_data.get("image"),
                league_data["season_id"],
                league_data["season_year"]
            ))
            
            conn.commit()
            return league_data["id"]
    
    def save_team(self, team_data: Dict, league_id: int, season_id: int) -> int:
        """Salva um time no banco de dados"""
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            
            # Validação de dados do time
            team_id = team_data.get("id")
            team_name = team_data.get("name", "").strip()
            
            if not team_id:
                logger.warning(f"ID do time não encontrado: {team_data}")
                return None
            
            if not team_name:
                logger.warning(f"Nome do time vazio para ID {team_id}")
                return None
            
            # Verifica se já existe um time com este ID para esta liga e temporada
            cursor.execute("""
                SELECT id FROM teams 
                WHERE id = ? AND league_id = ? AND season_id = ?
            """, (team_id, league_id, season_id))
            
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Atualiza registro existente
                cursor.execute("""
                    UPDATE teams SET
                        name = ?, clean_name = ?, english_name = ?, short_hand = ?, country = ?, continent = ?,
                        founded = ?, image = ?, flag_element = ?, season = ?, season_clean = ?, url = ?, table_position = ?,
                        performance_rank = ?, risk = ?, season_format = ?, competition_id = ?, full_name = ?,
                        alt_names = ?, official_sites = ?
                    WHERE id = ? AND league_id = ? AND season_id = ?
                """, (
                    team_name,
                    team_data.get("cleanName") or None,
                    team_data.get("english_name") or None,
                    team_data.get("shortHand") or None,
                    team_data.get("country") or None,
                    team_data.get("continent") or None,
                    team_data.get("founded") or None,
                    team_data.get("image") or None,
                    team_data.get("flag_element") or None,
                    team_data.get("season") or None,
                    team_data.get("seasonClean") or None,
                    team_data.get("url") or None,
                    team_data.get("table_position") or None,
                    team_data.get("performance_rank") or None,
                    team_data.get("risk") or None,
                    team_data.get("season_format") or None,
                    team_data.get("competition_id") or None,
                    team_data.get("full_name") or None,
                    str(team_data.get("alt_names", [])),  # Converte lista para string
                    str(team_data.get("official_sites", [])),  # Converte lista para string
                    team_id, league_id, season_id
                ))
                logger.debug(f"Time atualizado: ID {team_id} - {team_name}")
            else:
                # Insere novo registro
                cursor.execute("""
                    INSERT INTO teams (
                        id, name, clean_name, english_name, short_hand, country, continent,
                        founded, image, flag_element, season, season_clean, url, table_position,
                        performance_rank, risk, season_format, competition_id, full_name,
                        alt_names, official_sites, league_id, season_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    team_id,
                    team_name,
                    team_data.get("cleanName") or None,
                    team_data.get("english_name") or None,
                    team_data.get("shortHand") or None,
                    team_data.get("country") or None,
                    team_data.get("continent") or None,
                    team_data.get("founded") or None,
                    team_data.get("image") or None,
                    team_data.get("flag_element") or None,
                    team_data.get("season") or None,
                    team_data.get("seasonClean") or None,
                    team_data.get("url") or None,
                    team_data.get("table_position") or None,
                    team_data.get("performance_rank") or None,
                    team_data.get("risk") or None,
                    team_data.get("season_format") or None,
                    team_data.get("competition_id") or None,
                    team_data.get("full_name") or None,
                    str(team_data.get("alt_names", [])),  # Converte lista para string
                    str(team_data.get("official_sites", [])),  # Converte lista para string
                    league_id,
                    season_id
                ))
                logger.debug(f"Time salvo: ID {team_id} - {team_name}")
            
            conn.commit()
            return team_data["id"]
    
    def save_fixture(self, fixture_data: Dict, league_id: int, season_id: int) -> int:
        """Salva uma partida no banco de dados adaptada para FootyStats"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                # Extrai dados da partida baseado na estrutura real da API FootyStats
                fixture_id = fixture_data.get("id")
                home_team_id = fixture_data.get("homeID")
                away_team_id = fixture_data.get("awayID")
                home_team_name = fixture_data.get("home_name", "Unknown")
                away_team_name = fixture_data.get("away_name", "Unknown")
                
                # Validação básica de dados obrigatórios
                if not fixture_id:
                    logger.warning(f"ID da partida não encontrado: {fixture_data}")
                    return None
                
                if not home_team_id or not away_team_id:
                    logger.warning(f"IDs dos times não encontrados para partida {fixture_id}")
                    return None
                
                # Converte timestamp unix para datetime
                date_unix = fixture_data.get("date_unix")
                date_str = None
                if date_unix:
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(date_unix).strftime("%Y-%m-%d %H:%M:%S")
                
                # Verifica se já existe uma partida com este ID
                cursor.execute("SELECT id FROM fixtures WHERE id = ?", (fixture_id,))
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # Atualiza registro existente
                    cursor.execute("""
                        UPDATE fixtures SET
                            league_id = ?, season_id = ?, home_team_id = ?, away_team_id = ?,
                            home_team_name = ?, away_team_name = ?, home_team_url = ?, away_team_url = ?,
                            home_team_image = ?, away_team_image = ?, season = ?, status = ?, round_id = ?,
                            game_week = ?, revised_game_week = ?, home_goals = ?, away_goals = ?,
                            home_goal_count = ?, away_goal_count = ?, total_goal_count = ?,
                            home_corners = ?, away_corners = ?, total_corner_count = ?,
                            home_offsides = ?, away_offsides = ?, home_yellow_cards = ?, away_yellow_cards = ?,
                            home_red_cards = ?, away_red_cards = ?, home_shots_on_target = ?, away_shots_on_target = ?,
                            home_shots_off_target = ?, away_shots_off_target = ?, home_shots = ?, away_shots = ?,
                            home_fouls = ?, away_fouls = ?, home_possession = ?, away_possession = ?,
                            referee_id = ?, stadium_name = ?, stadium_location = ?, home_cards_num = ?, away_cards_num = ?,
                            home_halftime_goals = ?, away_halftime_goals = ?, goals_2hg_home = ?, goals_2hg_away = ?,
                            goal_count_2hg = ?, ht_goal_count = ?, date_unix = ?, winning_team = ?, btts_potential = ?,
                            attendance = ?, home_xg = ?, away_xg = ?, total_xg = ?, match_url = ?, competition_id = ?,
                            over05 = ?, over15 = ?, over25 = ?, over35 = ?, over45 = ?, over55 = ?, btts = ?,
                            home_goals_timings = ?, away_goals_timings = ?
                        WHERE id = ?
                    """, (
                        league_id, season_id, home_team_id, away_team_id,
                        home_team_name, away_team_name,
                        fixture_data.get("home_url"),
                        fixture_data.get("away_url"),
                        fixture_data.get("home_image"),
                        fixture_data.get("away_image"),
                        fixture_data.get("season"),
                        fixture_data.get("status", "Unknown"),
                        fixture_data.get("roundID"),
                        fixture_data.get("game_week"),
                        fixture_data.get("revised_game_week"),
                        str(fixture_data.get("homeGoals", [])),
                        str(fixture_data.get("awayGoals", [])),
                        fixture_data.get("homeGoalCount", 0),
                        fixture_data.get("awayGoalCount", 0),
                        fixture_data.get("totalGoalCount", 0),
                        fixture_data.get("team_a_corners", 0),
                        fixture_data.get("team_b_corners", 0),
                        fixture_data.get("totalCornerCount", 0),
                        fixture_data.get("team_a_offsides", 0),
                        fixture_data.get("team_b_offsides", 0),
                        fixture_data.get("team_a_yellow_cards", 0),
                        fixture_data.get("team_b_yellow_cards", 0),
                        fixture_data.get("team_a_red_cards", 0),
                        fixture_data.get("team_b_red_cards", 0),
                        fixture_data.get("team_a_shotsOnTarget", 0),
                        fixture_data.get("team_b_shotsOnTarget", 0),
                        fixture_data.get("team_a_shotsOffTarget", 0),
                        fixture_data.get("team_b_shotsOffTarget", 0),
                        fixture_data.get("team_a_shots", 0),
                        fixture_data.get("team_b_shots", 0),
                        fixture_data.get("team_a_fouls", 0),
                        fixture_data.get("team_b_fouls", 0),
                        fixture_data.get("team_a_possession", 0),
                        fixture_data.get("team_b_possession", 0),
                        fixture_data.get("refereeID"),
                        fixture_data.get("stadium_name"),
                        fixture_data.get("stadium_location"),
                        fixture_data.get("team_a_cards_num", 0),
                        fixture_data.get("team_b_cards_num", 0),
                        fixture_data.get("ht_goals_team_a", 0),
                        fixture_data.get("ht_goals_team_b", 0),
                        fixture_data.get("goals_2hg_team_a", 0),
                        fixture_data.get("goals_2hg_team_b", 0),
                        fixture_data.get("GoalCount_2hg", 0),
                        fixture_data.get("HTGoalCount", 0),
                        fixture_data.get("date_unix"),
                        fixture_data.get("winningTeam"),
                        fixture_data.get("btts_potential", 0),
                        fixture_data.get("attendance", -1),
                        fixture_data.get("team_a_xg", 0.0),
                        fixture_data.get("team_b_xg", 0.0),
                        fixture_data.get("total_xg", 0.0),
                        fixture_data.get("match_url"),
                        fixture_data.get("competition_id"),
                        fixture_data.get("over05", False),
                        fixture_data.get("over15", False),
                        fixture_data.get("over25", False),
                        fixture_data.get("over35", False),
                        fixture_data.get("over45", False),
                        fixture_data.get("over55", False),
                        fixture_data.get("btts", False),
                        str(fixture_data.get("homeGoals_timings", [])),
                        str(fixture_data.get("awayGoals_timings", [])),
                        fixture_id
                    ))
                    logger.debug(f"Partida atualizada: ID {fixture_id} - {home_team_name} vs {away_team_name}")
                else:
                    # Insere novo registro
                    cursor.execute("""
                        INSERT INTO fixtures (
                            id, league_id, season_id, home_team_id, away_team_id,
                            home_team_name, away_team_name, home_team_url, away_team_url,
                            home_team_image, away_team_image, season, status, round_id,
                            game_week, revised_game_week, home_goals, away_goals,
                            home_goal_count, away_goal_count, total_goal_count,
                            home_corners, away_corners, total_corner_count,
                            home_offsides, away_offsides, home_yellow_cards, away_yellow_cards,
                            home_red_cards, away_red_cards, home_shots_on_target, away_shots_on_target,
                            home_shots_off_target, away_shots_off_target, home_shots, away_shots,
                            home_fouls, away_fouls, home_possession, away_possession,
                            referee_id, stadium_name, stadium_location, home_cards_num, away_cards_num,
                            home_halftime_goals, away_halftime_goals, goals_2hg_home, goals_2hg_away,
                            goal_count_2hg, ht_goal_count, date_unix, winning_team, btts_potential,
                            attendance, home_xg, away_xg, total_xg, match_url, competition_id,
                            over05, over15, over25, over35, over45, over55, btts,
                            home_goals_timings, away_goals_timings
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        fixture_id,
                        league_id,
                        season_id,
                        home_team_id,
                        away_team_id,
                        home_team_name,
                        away_team_name,
                        fixture_data.get("home_url"),
                        fixture_data.get("away_url"),
                        fixture_data.get("home_image"),
                        fixture_data.get("away_image"),
                        fixture_data.get("season"),
                        fixture_data.get("status", "Unknown"),
                        fixture_data.get("roundID"),
                        fixture_data.get("game_week"),
                        fixture_data.get("revised_game_week"),
                        str(fixture_data.get("homeGoals", [])),
                        str(fixture_data.get("awayGoals", [])),
                        fixture_data.get("homeGoalCount", 0),
                        fixture_data.get("awayGoalCount", 0),
                        fixture_data.get("totalGoalCount", 0),
                        fixture_data.get("team_a_corners", 0),
                        fixture_data.get("team_b_corners", 0),
                        fixture_data.get("totalCornerCount", 0),
                        fixture_data.get("team_a_offsides", 0),
                        fixture_data.get("team_b_offsides", 0),
                        fixture_data.get("team_a_yellow_cards", 0),
                        fixture_data.get("team_b_yellow_cards", 0),
                        fixture_data.get("team_a_red_cards", 0),
                        fixture_data.get("team_b_red_cards", 0),
                        fixture_data.get("team_a_shotsOnTarget", 0),
                        fixture_data.get("team_b_shotsOnTarget", 0),
                        fixture_data.get("team_a_shotsOffTarget", 0),
                        fixture_data.get("team_b_shotsOffTarget", 0),
                        fixture_data.get("team_a_shots", 0),
                        fixture_data.get("team_b_shots", 0),
                        fixture_data.get("team_a_fouls", 0),
                        fixture_data.get("team_b_fouls", 0),
                        fixture_data.get("team_a_possession", 0),
                        fixture_data.get("team_b_possession", 0),
                        fixture_data.get("refereeID"),
                        fixture_data.get("stadium_name"),
                        fixture_data.get("stadium_location"),
                        fixture_data.get("team_a_cards_num", 0),
                        fixture_data.get("team_b_cards_num", 0),
                        fixture_data.get("ht_goals_team_a", 0),
                        fixture_data.get("ht_goals_team_b", 0),
                        fixture_data.get("goals_2hg_team_a", 0),
                        fixture_data.get("goals_2hg_team_b", 0),
                        fixture_data.get("GoalCount_2hg", 0),
                        fixture_data.get("HTGoalCount", 0),
                        fixture_data.get("date_unix"),
                        fixture_data.get("winningTeam"),
                        fixture_data.get("btts_potential", 0),
                        fixture_data.get("attendance", -1),
                        fixture_data.get("team_a_xg", 0.0),
                        fixture_data.get("team_b_xg", 0.0),
                        fixture_data.get("total_xg", 0.0),
                        fixture_data.get("match_url"),
                        fixture_data.get("competition_id"),
                        fixture_data.get("over05", False),
                        fixture_data.get("over15", False),
                        fixture_data.get("over25", False),
                        fixture_data.get("over35", False),
                        fixture_data.get("over45", False),
                        fixture_data.get("over55", False),
                        fixture_data.get("btts", False),
                        str(fixture_data.get("homeGoals_timings", [])),
                        str(fixture_data.get("awayGoals_timings", []))
                    ))
                    logger.debug(f"Partida salva: ID {fixture_id} - {home_team_name} vs {away_team_name}")
                
                conn.commit()
                return fixture_id
                
        except Exception as e:
            logger.error(f"Erro ao salvar partida: {e}")
            return None
    
    def save_team_statistics(self, team_stats: Dict, league_id: int, season_id: int, season_year: int) -> bool:
        """Salva estatísticas de um time no banco de dados"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                # Adapta os dados da FootyStats para o formato interno
                team_id = team_stats.get("team_id") or team_stats.get("id")
                if not team_id:
                    logger.warning(f"ID do time não encontrado: {team_stats}")
                    return False
                
                cursor.execute("""
                    INSERT OR REPLACE INTO team_statistics (
                        team_id, league_id, season_id, season_year, matches_played, wins, draws, losses,
                        goals_for, goals_against, points, rank, position
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    team_id,
                    league_id,
                    season_id,
                    season_year,
                    team_stats.get("matches_played", 0),
                    team_stats.get("wins", 0),
                    team_stats.get("draws", 0),
                    team_stats.get("losses", 0),
                    team_stats.get("goals_for", 0),
                    team_stats.get("goals_against", 0),
                    team_stats.get("points", 0),
                    team_stats.get("rank", 0),
                    team_stats.get("position", 0)
                ))
                
                conn.commit()
                logger.debug(f"Estatísticas do time {team_id} salvas")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao salvar estatísticas do time: {e}")
            return False
    
    def save_player(self, player_data: Dict, team_id: int, league_id: int, season_id: int) -> int:
        """Salva dados de um jogador no banco de dados"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                # Obtém nome do time
                cursor.execute("SELECT name FROM teams WHERE id = ?", (team_id,))
                team_result = cursor.fetchone()
                team_name = team_result[0] if team_result else "Unknown"
                
                # Validação de dados do jogador
                player_name = player_data.get("name", "").strip()
                if not player_name or player_name == "N/A" or player_name == "Unknown":
                    logger.debug(f"⏭️  Jogador sem nome válido pulado para team_id {team_id}: '{player_name}'")
                    return None
                
                # Verifica se já existe um jogador com este nome para este time e temporada
                cursor.execute("""
                    SELECT id FROM players 
                    WHERE name = ? AND team_id = ? AND season_id = ?
                """, (player_name, team_id, season_id))
                
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # Atualiza registro existente
                    cursor.execute("""
                        UPDATE players SET
                            team_name = ?, position = ?, goals = ?, assists = ?, 
                            matches_played = ?, league_id = ?, age = ?, height = ?, weight = ?, url = ?,
                            minutes_played = ?, clean_sheets = ?, yellow_cards = ?, red_cards = ?
                        WHERE name = ? AND team_id = ? AND season_id = ?
                    """, (
                        team_name,
                        player_data.get("position", ""),
                        player_data.get("goals", 0) or 0,
                        player_data.get("assists", 0) or 0,
                        player_data.get("matches_played", 0) or 0,
                        league_id,
                        player_data.get("age") or None,
                        player_data.get("height") or None,
                        player_data.get("weight") or None,
                        player_data.get("url") or None,
                        player_data.get("minutes_played", 0) or 0,
                        player_data.get("clean_sheets", 0) or 0,
                        player_data.get("yellow_cards", 0) or 0,
                        player_data.get("red_cards", 0) or 0,
                        player_name, team_id, season_id
                    ))
                    logger.debug(f"Jogador atualizado: {player_name} - {team_name}")
                    return existing_record[0]
                else:
                    # Insere novo registro
                    cursor.execute("""
                        INSERT INTO players (
                            name, team_id, team_name, position, goals, assists, 
                            matches_played, league_id, season_id, age, height, weight, url,
                            minutes_played, clean_sheets, yellow_cards, red_cards
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        player_name,
                        team_id,
                        team_name,
                        player_data.get("position", ""),
                        player_data.get("goals", 0) or 0,
                        player_data.get("assists", 0) or 0,
                        player_data.get("matches_played", 0) or 0,
                        league_id,
                        season_id,
                        player_data.get("age") or None,
                        player_data.get("height") or None,
                        player_data.get("weight") or None,
                        player_data.get("url") or None,
                        player_data.get("minutes_played", 0) or 0,
                        player_data.get("clean_sheets", 0) or 0,
                        player_data.get("yellow_cards", 0) or 0,
                        player_data.get("red_cards", 0) or 0
                    ))
                    logger.debug(f"Jogador salvo: {player_name} - {team_name}")
                    return cursor.lastrowid
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Erro ao salvar jogador: {e}")
            return None
    
    def save_match_player(self, match_id: int, player_data: Dict, team_id: int) -> int:
        """Salva dados de um jogador em uma partida específica"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                player_name = player_data.get("name", "").strip()
                if not player_name:
                    logger.warning(f"Nome do jogador vazio para match_id {match_id}")
                    return None
                
                # Verifica se já existe um jogador com este nome para esta partida e time
                cursor.execute("""
                    SELECT id FROM match_players 
                    WHERE match_id = ? AND player_name = ? AND team_id = ?
                """, (match_id, player_name, team_id))
                
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # Atualiza registro existente
                    cursor.execute("""
                        UPDATE match_players SET
                            goals = ?, assists = ?, position = ?
                        WHERE match_id = ? AND player_name = ? AND team_id = ?
                    """, (
                        player_data.get("goals", 0),
                        player_data.get("assists", 0),
                        player_data.get("position", ""),
                        match_id, player_name, team_id
                    ))
                    logger.debug(f"Jogador da partida atualizado: {player_name} - Match {match_id}")
                    return existing_record[0]
                else:
                    # Insere novo registro
                    cursor.execute("""
                        INSERT INTO match_players (
                            match_id, player_name, team_id, goals, assists, position
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        match_id,
                        player_name,
                        team_id,
                        player_data.get("goals", 0),
                        player_data.get("assists", 0),
                        player_data.get("position", "")
                    ))
                    logger.debug(f"Jogador da partida salvo: {player_name} - Match {match_id}")
                    return cursor.lastrowid
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Erro ao salvar jogador da partida: {e}")
            return None
    
    def collect_players_data(self, league_config: LeagueConfig):
        logger.info(f"👥 Coletando dados de jogadores da liga: {league_config.name}")
        
        try:
            # Obtém lista de jogadores da API
            logger.info("📊 Obtendo lista de jogadores da API...")
            players_list = self.api.get_league_players(league_config.season_id)
            
            if not players_list:
                logger.warning("⚠️ Nenhum jogador encontrado na API")
                return
            
            logger.info(f"📊 Encontrados {len(players_list)} jogadores na API")
            
            # Mapeia jogadores por time
            players_by_team = {}
            for player in players_list:
                team_id = player.get("club_team_id")
                if team_id and team_id != -1:
                    if team_id not in players_by_team:
                        players_by_team[team_id] = []
                    players_by_team[team_id].append(player)
            
            logger.info(f"📊 Jogadores distribuídos em {len(players_by_team)} times")
            
            # Salva jogadores no banco
            total_saved = 0
            batch_size = 200
            
            all_players_data = []
            for team_id, team_players in players_by_team.items():
                logger.info(f"💾 Processando {len(team_players)} jogadores do time {team_id}")
                
                for player in team_players:
                    # Tenta diferentes campos para o nome do jogador
                    player_name = (player.get("full_name") or 
                                 player.get("name") or 
                                 player.get("player_name") or 
                                 f"Jogador_{player.get('id', 'Unknown')}")
                    
                    # Se ainda estiver vazio, pula este jogador
                    if not player_name or player_name.strip() == "":
                        logger.debug(f"⏭️  Jogador sem nome válido pulado: {player}")
                        continue
                    
                    # Os dados já vêm com estatísticas incluídas!
                    player_data = {
                        "name": player_name.strip(),
                        "position": player.get("position", "N/A"),
                        "goals": player.get("goals_overall", 0),
                        "assists": player.get("assists_overall", 0),
                        "matches_played": player.get("appearances_overall", 0),
                        "age": player.get("age"),
                        "height": player.get("height"),
                        "weight": player.get("weight"),
                        "url": player.get("url"),
                        "minutes_played": player.get("minutes_played_overall", 0),
                        "clean_sheets": player.get("clean_sheets_overall", 0),
                        "yellow_cards": player.get("yellow_cards_overall", 0),
                        "red_cards": player.get("red_cards_overall", 0)
                    }

                    all_players_data.append((player_data, team_id, league_config.id, league_config.season_id))
            
            # Processa jogadores em lotes
            for i in range(0, len(all_players_data), batch_size):
                batch = all_players_data[i:i + batch_size]
                logger.info(f"💾 Salvando lote de {len(batch)} jogadores...")
                
                for player_data, team_id, league_id, season_id in batch:
                    # Salva no banco
                    saved_player_id = self.save_player(player_data, team_id, league_id, season_id)
                    if saved_player_id:
                        total_saved += 1
            
            logger.info(f"✅ {total_saved} jogadores salvos com sucesso!")
                
        except Exception as e:
            logger.error(f"❌ Erro ao coletar dados de jogadores: {e}")
    
    def get_league_top_scorers_from_db(self, league_id: int) -> List[Dict]:
        """Obtém artilharia do banco de dados local"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        p.name,
                        p.team_name,
                        p.position,
                        p.goals,
                        p.assists,
                        p.matches_played,
                        t.image as team_logo,
                        p.url
                    FROM players p
                    LEFT JOIN teams t ON p.team_id = t.id
                    WHERE p.league_id = ? AND p.goals > 0
                    GROUP BY p.name, p.team_name
                    ORDER BY p.goals DESC, p.assists DESC
                    LIMIT 20
                """, (league_id,))
                
                results = cursor.fetchall()
                scorers = []
                
                for row in results:
                    name, team_name, position, goals, assists, matches, team_logo, player_url = row
                    
                    # Gera URL da foto do jogador com nacionalidade
                    player_photo = self._generate_player_photo_url(name, player_url)
                    
                    scorers.append({
                        "jogador-nome": name,
                        "jogador-posicao": position or "N/A",
                        "jogador-gols": goals,
                        "jogador-assists": assists,
                        "jogador-partidas": matches,
                        "jogador-escudo": team_logo or "",
                        "jogador-foto": player_photo
                    })
                
                return scorers
                
        except Exception as e:
            logger.error(f"Erro ao obter artilharia do banco: {e}")
            return []

    def _generate_player_photo_url(self, player_name: str, player_url: str = None) -> str:
        """Gera URL da foto do jogador incluindo nacionalidade extraída da URL"""
        try:
            # Se não há URL do jogador, usa formato padrão sem nacionalidade
            if not player_url:
                return f"https://cdn.footystats.org/img/players/-{player_name.lower().replace(' ', '-')}.png"
            
            url_parts = player_url.split('/')
            if len(url_parts) >= 6 and url_parts[3] == 'players':
                nationality = url_parts[4]  # Ex: 'brazil'
                url_player_name = url_parts[5]  # Ex: 'kaio-jorge' ou 'kaio-jorge-pinto-ramos'
                return f"https://cdn.footystats.org/img/players/{nationality}-{url_player_name}.png"
            else:
                # Fallback para formato sem nacionalidade
                return f"https://cdn.footystats.org/img/players/-{player_name.lower().replace(' ', '-')}.png"
                
        except Exception as e:
            logger.warning(f"Erro ao gerar URL da foto para {player_name}: {e}")
            # Fallback para formato sem nacionalidade
            return f"https://cdn.footystats.org/img/players/-{player_name.lower().replace(' ', '-')}.png"

    def collect_league_data(self, league_config: LeagueConfig):
        """Coleta todos os dados de uma liga"""
        logger.info(f"🏆 Iniciando coleta da liga: {league_config.name} {league_config.season_year} (Season ID: {league_config.season_id})")
        
        # Salva a liga
        league_data = {
            "id": league_config.id,
            "name": league_config.name,
            "country": league_config.country,
            "image": None,
            "season_id": league_config.season_id,
            "season_year": league_config.season_year
        }
        self.save_league(league_data)
        logger.info(f"✅ Liga {league_config.name} {league_config.season_year} salva no banco")
        
        # Obtém times da liga
        teams = self.api.get_league_teams(league_config.season_id)
        logger.info(f"👥 Encontrados {len(teams)} times na liga")
        
        teams_processed = set()
        for team in teams:
            if team.get("id") and team["id"] not in teams_processed:
                self.save_team(team, league_config.id, league_config.season_id)
                logger.debug(f"✅ Time processado: {team.get('name', 'N/A')}")
                teams_processed.add(team["id"])
        
        # Obtém todas as partidas PRIMEIRO
        fixtures = self.api.get_league_matches(league_config.season_id)
        logger.info(f"📋 Encontradas {len(fixtures)} partidas na API")
        
        fixtures_processed = 0
        fixtures_skipped = 0
        
        # Processa partidas em lotes para otimização
        batch_size = 50
        for i in range(0, len(fixtures), batch_size):
            batch = fixtures[i:i + batch_size]
            
            # Log de progresso
            logger.info(f"🔄 Progresso: {i + len(batch)}/{len(fixtures)} partidas processadas")
            
            # Processa lote de partidas
            for fixture in batch:
                fixture_id = fixture.get("id")
                
                # Salva a partida (o método save_fixture já verifica duplicatas)
                saved_fixture_id = self.save_fixture(fixture, league_config.id, league_config.season_id)
                
                if saved_fixture_id:
                    fixtures_processed += 1
                    home_team = fixture.get("home_name", "N/A")
                    away_team = fixture.get("away_name", "N/A")
                    logger.debug(f"✅ Partida salva: {saved_fixture_id} - {home_team} vs {away_team}")
            
            # Delay reduzido apenas entre lotes
            if i + batch_size < len(fixtures):
                time.sleep(0.05)
        
        
        # Coleta dados de jogadores
        logger.info("👥 Coletando dados de jogadores...")
        self.collect_players_data(league_config)
        
        # Constrói tabela de classificação APÓS coletar as partidas
        logger.info("📊 Construindo tabela de classificação a partir dos dados coletados...")
        self.build_league_table_from_matches(league_config.id, league_config.season_id, league_config.season_year)
        
        # Resumo final
        logger.info(f"🎯 Resumo da coleta - {league_config.name} {league_config.season_year}:")
        logger.info(f"   📋 Partidas: {fixtures_processed} novas, {fixtures_skipped} puladas")
        logger.info(f"   👥 Times processados: {len(teams_processed)}")
        logger.info(f"✅ Dados da liga {league_config.name} {league_config.season_year} coletados com sucesso")
    
    def collect_all_data(self):
        """Coleta dados de todas as ligas configuradas com processamento paralelo"""
        start_time = time.time()
        logger.info("🚀 Iniciando coleta de dados de todas as ligas")
        
        # Carrega ligas da API
        self.load_leagues_from_api()
        logger.info(f"📋 Total de ligas carregadas: {len(self.leagues)}")
        
        successful_leagues = 0
        failed_leagues = 0
        
        # Processa ligas em paralelo para otimização
        max_workers = min(3, len(self.leagues))
        logger.info(f"🔄 Processando {len(self.leagues)} ligas em paralelo (max {max_workers} threads)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submete todas as ligas para processamento paralelo
            future_to_league = {
                executor.submit(self._process_league_safe, league_config): league_config 
                for league_config in self.leagues
            }
            
            # Processa resultados conforme completam
            for future in as_completed(future_to_league):
                league_config = future_to_league[future]
                try:
                    result = future.result()
                    if result:
                        successful_leagues += 1
                        logger.info(f"✅ Liga {league_config.name} {league_config.season_year} processada com sucesso")
                    else:
                        failed_leagues += 1
                        logger.error(f"❌ Liga {league_config.name} {league_config.season_year} falhou")
                except Exception as e:
                    failed_leagues += 1
                    logger.error(f"❌ Erro ao processar liga {league_config.name} {league_config.season_year}: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info("🎯 Resumo final da coleta:")
        logger.info(f"   ✅ Ligas processadas com sucesso: {successful_leagues}")
        logger.info(f"   ❌ Ligas com erro: {failed_leagues}")
        logger.info(f"   ⏱️  Tempo total de execução: {duration:.2f} segundos")
        logger.info("🏁 Coleta de dados concluída")
    
    def _process_league_safe(self, league_config):
        """Processa uma liga de forma thread-safe"""
        try:
            # Cria uma nova instância do API client para cada thread
            thread_api = FootyStatsAPIClient(api_key=os.getenv("FOOTYSTATS_API_KEY"))
            thread_collector = FootballDataCollector()
            thread_collector.api = thread_api
            thread_collector.db = self.db
            
            # Processa a liga
            thread_collector.collect_league_data(league_config)
            return True
        except Exception as e:
            logger.error(f"❌ Erro na thread para liga {league_config.name}: {e}")
            return False
    
    def build_league_table_from_matches(self, league_id: int, season_id: int, season_year: int = None):
        """Constrói tabela de classificação a partir dos dados de partidas coletados"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                # Obtém todos os times da liga usando season_id como identificador único
                cursor.execute("SELECT id, name FROM teams WHERE season_id = ?", (season_id,))
                teams = cursor.fetchall()
                
                if not teams:
                    logger.warning(f"Nenhum time encontrado para liga {league_id}")
                    return
                
                # Para cada time, calcula estatísticas
                for team_id, team_name in teams:
                    # Partidas como mandante (apenas completas)
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as matches,
                            SUM(CASE WHEN home_goal_count > away_goal_count THEN 1 ELSE 0 END) as wins,
                            SUM(CASE WHEN home_goal_count = away_goal_count THEN 1 ELSE 0 END) as draws,
                            SUM(CASE WHEN home_goal_count < away_goal_count THEN 1 ELSE 0 END) as losses,
                            SUM(home_goal_count) as goals_for,
                            SUM(away_goal_count) as goals_against
                        FROM fixtures 
                        WHERE season_id = ? AND home_team_id = ? AND status = 'complete'
                    """, (season_id, team_id))
                    
                    home_stats = cursor.fetchone()
                    
                    # Partidas como visitante (apenas completas)
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as matches,
                            SUM(CASE WHEN away_goal_count > home_goal_count THEN 1 ELSE 0 END) as wins,
                            SUM(CASE WHEN away_goal_count = home_goal_count THEN 1 ELSE 0 END) as draws,
                            SUM(CASE WHEN away_goal_count < home_goal_count THEN 1 ELSE 0 END) as losses,
                            SUM(away_goal_count) as goals_for,
                            SUM(home_goal_count) as goals_against
                        FROM fixtures 
                        WHERE season_id = ? AND away_team_id = ? AND status = 'complete'
                    """, (season_id, team_id))
                    
                    away_stats = cursor.fetchone()
                    
                    # Calcula totais
                    total_matches = (home_stats[0] or 0) + (away_stats[0] or 0)
                    total_wins = (home_stats[1] or 0) + (away_stats[1] or 0)
                    total_draws = (home_stats[2] or 0) + (away_stats[2] or 0)
                    total_losses = (home_stats[3] or 0) + (away_stats[3] or 0)
                    total_goals_for = (home_stats[4] or 0) + (away_stats[4] or 0)
                    total_goals_against = (home_stats[5] or 0) + (away_stats[5] or 0)
                    total_points = (total_wins * 3) + (total_draws * 1)
                    
                    # Verifica se já existe estatística para este time/liga/temporada
                    cursor.execute("""
                        SELECT id FROM team_statistics 
                        WHERE team_id = ? AND league_id = ? AND season_id = ?
                    """, (team_id, league_id, season_id))
                    
                    existing_record = cursor.fetchone()
                    
                    if existing_record:
                        # Atualiza registro existente
                        cursor.execute("""
                            UPDATE team_statistics SET
                                season_year = ?, matches_played = ?, wins = ?, draws = ?, losses = ?,
                                goals_for = ?, goals_against = ?, points = ?, rank = 0, position = 0
                            WHERE team_id = ? AND league_id = ? AND season_id = ?
                        """, (
                            season_year or 2025, total_matches, total_wins, total_draws, total_losses,
                            total_goals_for, total_goals_against, total_points,
                            team_id, league_id, season_id
                        ))
                    else:
                        # Insere novo registro
                        cursor.execute("""
                            INSERT INTO team_statistics (
                                team_id, league_id, season_id, season_year, matches_played, wins, draws, losses,
                                goals_for, goals_against, points, rank, position
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            team_id, league_id, season_id, season_year or 2025, total_matches, total_wins, total_draws, total_losses,
                            total_goals_for, total_goals_against, total_points, 0, 0
                        ))
                
                # Atualiza posições na tabela seguindo critérios de desempate:
                # 1) Maior número de vitórias; 2) Maior saldo de gols; 3) Maior número de gols pró;
                # 4) Confronto direto (entre clubes empatados nos critérios anteriores);
                # 5) Menor número de cartões vermelhos; 6) Menor número de cartões amarelos.
                # Implementação: calculamos as chaves de desempate em Python e persistimos rank/position.

                # Carrega estatísticas atuais dos times nesta temporada
                cursor.execute("""
                    SELECT team_id, points, wins, (goals_for - goals_against) as gd, goals_for
                    FROM team_statistics
                    WHERE league_id = ? AND season_id = ?
                """, (league_id, season_id))
                rows = cursor.fetchall()

                # Mapa base por time
                team_rows = {
                    row[0]: {
                        "team_id": row[0],
                        "points": row[1] or 0,
                        "wins": row[2] or 0,
                        "gd": row[3] or 0,
                        "gf": row[4] or 0,
                        "h2h_points": 0,
                        "red_cards": 0,
                        "yellow_cards": 0,
                    }
                    for row in rows
                }

                if team_rows:
                    team_ids = tuple(team_rows.keys())

                    # Cartões por time (soma home/away)
                    # Nota: status 'complete' garante partidas encerradas
                    placeholders = ",".join(["?"] * len(team_ids))
                    cards_query = f"""
                        SELECT ts.team_id,
                               COALESCE(SUM(CASE 
                                    WHEN f.home_team_id = ts.team_id THEN f.home_red_cards 
                                    WHEN f.away_team_id = ts.team_id THEN f.away_red_cards 
                                    ELSE 0 END), 0) AS red_cards,
                               COALESCE(SUM(CASE 
                                    WHEN f.home_team_id = ts.team_id THEN f.home_yellow_cards 
                                    WHEN f.away_team_id = ts.team_id THEN f.away_yellow_cards 
                                    ELSE 0 END), 0) AS yellow_cards
                        FROM team_statistics ts
                        JOIN fixtures f 
                          ON f.league_id = ts.league_id 
                         AND f.season_id = ts.season_id
                         AND f.status = 'complete'
                         AND (f.home_team_id = ts.team_id OR f.away_team_id = ts.team_id)
                        WHERE ts.league_id = ? AND ts.season_id = ? AND ts.team_id IN ({placeholders})
                        GROUP BY ts.team_id
                    """
                    cursor.execute(cards_query, (league_id, season_id, *team_ids))
                    for team_id, red_cards, yellow_cards in cursor.fetchall():
                        team_rows[team_id]["red_cards"] = red_cards or 0
                        team_rows[team_id]["yellow_cards"] = yellow_cards or 0

                    # Agrupa times empatados antes de confronto direto: pontos, vitórias, gd, gf
                    from collections import defaultdict
                    groups = defaultdict(list)
                    for t in team_rows.values():
                        groups[(t["points"], t["wins"], t["gd"], t["gf"])].append(t["team_id"])

                    # Calcula pontos de confronto direto por grupo com mais de 1 time
                    for key, tied_team_ids in groups.items():
                        if len(tied_team_ids) <= 1:
                            continue
                        tied_placeholders = ",".join(["?"] * len(tied_team_ids))
                        # Para cada time do grupo, soma pontos contra os demais do mesmo grupo
                        for team_id in tied_team_ids:
                            params = [league_id, season_id, team_id] + tied_team_ids + [team_id] + tied_team_ids
                            h2h_query = f"""
                                SELECT COALESCE(SUM(points_earned), 0) FROM (
                                    SELECT 
                                        CASE 
                                            WHEN f.home_team_id = ? THEN 
                                                CASE WHEN f.home_goal_count > f.away_goal_count THEN 3 
                                                     WHEN f.home_goal_count = f.away_goal_count THEN 1 
                                                     ELSE 0 END
                                            ELSE 
                                                CASE WHEN f.away_goal_count > f.home_goal_count THEN 3 
                                                     WHEN f.away_goal_count = f.home_goal_count THEN 1 
                                                     ELSE 0 END
                                        END AS points_earned
                                    FROM fixtures f
                                    WHERE f.league_id = ? AND f.season_id = ? AND f.status = 'complete'
                                      AND (
                                        (f.home_team_id = ? AND f.away_team_id IN ({tied_placeholders})) OR
                                        (f.away_team_id = ? AND f.home_team_id IN ({tied_placeholders}))
                                      )
                                )
                            """
                            cursor.execute(h2h_query, params)
                            h2h_points = cursor.fetchone()[0] or 0
                            team_rows[team_id]["h2h_points"] = h2h_points

                    # Ordena aplicando todos os critérios
                    sorted_teams = sorted(
                        team_rows.values(),
                        key=lambda t: (
                            -(t["points"]),
                            -(t["wins"]),
                            -(t["gd"]),
                            -(t["gf"]),
                            -(t["h2h_points"]),
                            (t["red_cards"]),
                            (t["yellow_cards"]),
                            t["team_id"],
                        )
                    )

                    # Atualiza rank e position conforme ordem calculada
                    for idx, t in enumerate(sorted_teams, start=1):
                        cursor.execute(
                            """
                            UPDATE team_statistics 
                            SET rank = ?, position = ?
                            WHERE league_id = ? AND season_id = ? AND team_id = ?
                            """,
                            (idx, idx, league_id, season_id, t["team_id"]))
                
                conn.commit()
                logger.info(f"✅ Tabela de classificação construída para liga {league_id}")
                
        except Exception as e:
            logger.error(f"Erro ao construir tabela de classificação: {e}")
    
    def export_league_data_to_json(self, league_id: int, output_file: str = None):
        """Exporta dados de uma liga para JSON no formato do example.json"""
        try:
            with sqlite3.connect(self.db.db_name) as conn:
                cursor = conn.cursor()
                
                # Obtém informações da liga
                cursor.execute("SELECT name, country FROM leagues WHERE id = ?", (league_id,))
                league_info = cursor.fetchone()
                
                if not league_info:
                    logger.error(f"Liga {league_id} não encontrada no banco de dados")
                    return None
                
                league_name = league_info[0]
                country = league_info[1]
                
                # Obtém tabela de classificação com estatísticas completas (sem duplicações)
                cursor.execute("""
                    SELECT 
                        ts.rank,
                        t.id as team_id,
                        t.name as team_name,
                        t.image as team_logo,
                        ts.points,
                        ts.goals_for - ts.goals_against as goals_diff,
                        ts.matches_played,
                        ts.wins,
                        ts.draws,
                        ts.losses,
                        ts.goals_for,
                        ts.goals_against
                    FROM team_statistics ts
                    JOIN teams t ON ts.team_id = t.id
                    WHERE ts.league_id = ?
                    GROUP BY ts.team_id, ts.league_id, ts.season_id
                    ORDER BY ts.rank
                """, (league_id,))
                
                standings_data = cursor.fetchall()
                
                # Formata os dados no padrão do example.json
                standings = []
                for row in standings_data:
                    rank, team_id, team_name, team_logo, points, goals_diff, played, wins, draws, losses, goals_for, goals_against = row
                    
                    # Obtém estatísticas HOME (quando o time joga EM CASA)
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as home_matches,
                            SUM(CASE WHEN COALESCE(home_goal_count, 0) > COALESCE(away_goal_count, 0) THEN 1 ELSE 0 END) as home_wins,
                            SUM(CASE WHEN COALESCE(home_goal_count, 0) = COALESCE(away_goal_count, 0) THEN 1 ELSE 0 END) as home_draws,
                            SUM(CASE WHEN COALESCE(home_goal_count, 0) < COALESCE(away_goal_count, 0) THEN 1 ELSE 0 END) as home_losses,
                            SUM(COALESCE(home_goal_count, 0)) as home_goals_for,
                            SUM(COALESCE(away_goal_count, 0)) as home_goals_against,
                            COUNT(CASE WHEN home_goal_count > 0 AND away_goal_count > 0 THEN 1 END) as btts_home,
                            COUNT(CASE WHEN COALESCE(home_goal_count, 0) + COALESCE(away_goal_count, 0) > 2.5 THEN 1 END) as over_2_5_home,
                            COUNT(CASE WHEN COALESCE(away_goal_count, 0) = 0 THEN 1 END) as clean_sheets_home,
                            COUNT(CASE WHEN COALESCE(home_halftime_goals, 0) > 0 THEN 1 END) as over_0_5_ht_home,
                            COUNT(CASE WHEN COALESCE(home_goal_count, 0) > COALESCE(home_halftime_goals, 0) THEN 1 END) as over_0_5_ft_home,
                            AVG(home_corners) as avg_corners_home
                        FROM fixtures f
                        WHERE f.league_id = ? AND f.home_team_id = ? AND f.status = 'complete'
                        AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL
                    """, (league_id, team_id))
                    
                    home_stats = cursor.fetchone()
                    
                    # Obtém estatísticas AWAY (quando o time joga FORA DE CASA)
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as away_matches,
                            SUM(CASE WHEN COALESCE(away_goal_count, 0) > COALESCE(home_goal_count, 0) THEN 1 ELSE 0 END) as away_wins,
                            SUM(CASE WHEN COALESCE(away_goal_count, 0) = COALESCE(home_goal_count, 0) THEN 1 ELSE 0 END) as away_draws,
                            SUM(CASE WHEN COALESCE(away_goal_count, 0) < COALESCE(home_goal_count, 0) THEN 1 ELSE 0 END) as away_losses,
                            SUM(COALESCE(away_goal_count, 0)) as away_goals_for,
                            SUM(COALESCE(home_goal_count, 0)) as away_goals_against,
                            COUNT(CASE WHEN home_goal_count > 0 AND away_goal_count > 0 THEN 1 END) as btts_away,
                            COUNT(CASE WHEN COALESCE(home_goal_count, 0) + COALESCE(away_goal_count, 0) > 2.5 THEN 1 END) as over_2_5_away,
                            COUNT(CASE WHEN COALESCE(home_goal_count, 0) = 0 THEN 1 END) as clean_sheets_away,
                            COUNT(CASE WHEN COALESCE(away_halftime_goals, 0) > 0 THEN 1 END) as over_0_5_ht_away,
                            COUNT(CASE WHEN COALESCE(away_goal_count, 0) > COALESCE(away_halftime_goals, 0) THEN 1 END) as over_0_5_ft_away,
                            AVG(away_corners) as avg_corners_away
                        FROM fixtures f
                        WHERE f.league_id = ? AND f.away_team_id = ? AND f.status = 'complete'
                        AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL
                    """, (league_id, team_id))
                    
                    away_stats = cursor.fetchone()
                    
                    # Calcula aproveitamento geral
                    aproveitamento = 0
                    if played > 0:
                        max_points = played * 3
                        aproveitamento = round((points / max_points) * 100, 1)
                    
                    # Calcula aproveitamento casa
                    aproveitamento_home = 0
                    home_played = home_stats[0] or 0
                    if home_played > 0:
                        home_points = (home_stats[1] or 0) * 3 + (home_stats[2] or 0) * 1
                        max_home_points = home_played * 3
                        aproveitamento_home = round((home_points / max_home_points) * 100, 1)
                    
                    # Calcula aproveitamento fora
                    aproveitamento_away = 0
                    away_played = away_stats[0] or 0
                    if away_played > 0:
                        away_points = (away_stats[1] or 0) * 3 + (away_stats[2] or 0) * 1
                        max_away_points = away_played * 3
                        aproveitamento_away = round((away_points / max_away_points) * 100, 1)
                    
                    # Obtém estatísticas GERAIS (todas as partidas do time)
                    cursor.execute("""
                        SELECT 
                            COUNT(CASE WHEN f.home_goal_count > 0 AND f.away_goal_count > 0 THEN 1 END) as btts_matches,
                            COUNT(CASE WHEN COALESCE(f.home_goal_count, 0) + COALESCE(f.away_goal_count, 0) > 2.5 THEN 1 END) as over_2_5_goals,
                            COUNT(CASE WHEN (f.home_team_id = ? AND COALESCE(f.away_goal_count, 0) = 0) OR 
                                             (f.away_team_id = ? AND COALESCE(f.home_goal_count, 0) = 0) THEN 1 END) as clean_sheets,
                            COUNT(CASE WHEN (f.home_team_id = ? AND COALESCE(f.home_halftime_goals, 0) > 0) OR 
                                             (f.away_team_id = ? AND COALESCE(f.away_halftime_goals, 0) > 0) THEN 1 END) as over_0_5_ht,
                            COUNT(CASE WHEN (f.home_team_id = ? AND COALESCE(f.home_goal_count, 0) > COALESCE(f.home_halftime_goals, 0)) OR 
                                             (f.away_team_id = ? AND COALESCE(f.away_goal_count, 0) > COALESCE(f.away_halftime_goals, 0)) THEN 1 END) as over_0_5_ft,
                            AVG(CASE WHEN f.home_team_id = ? THEN f.home_corners ELSE f.away_corners END) as avg_corners
                        FROM fixtures f
                        WHERE f.league_id = ? AND f.status = 'complete'
                        AND (f.home_team_id = ? OR f.away_team_id = ?)
                        AND f.home_goal_count IS NOT NULL AND f.away_goal_count IS NOT NULL
                    """, (team_id, team_id, team_id, team_id, team_id, team_id, team_id, league_id, team_id, team_id))
                    
                    general_stats = cursor.fetchone()
                    
                    # Gera form baseado nas últimas 5 partidas
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN (f.home_team_id = ? AND f.home_goal_count > f.away_goal_count) OR 
                                     (f.away_team_id = ? AND f.away_goal_count > f.home_goal_count) THEN 'W'
                                WHEN (f.home_team_id = ? AND f.home_goal_count = f.away_goal_count) OR 
                                     (f.away_team_id = ? AND f.away_goal_count = f.home_goal_count) THEN 'D'
                                ELSE 'L'
                            END as result
                        FROM fixtures f
                        WHERE f.league_id = ? AND f.status = 'complete'
                        AND (f.home_team_id = ? OR f.away_team_id = ?)
                        ORDER BY f.date_unix DESC
                        LIMIT 5
                    """, (team_id, team_id, team_id, team_id, league_id, team_id, team_id))
                    
                    form_results = cursor.fetchall()
                    form = ''.join([r[0] for r in reversed(form_results)]) if form_results else ""
                    
                    # Gera form home
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN f.home_goal_count > f.away_goal_count THEN 'W'
                                WHEN f.home_goal_count = f.away_goal_count THEN 'D'
                                ELSE 'L'
                            END as result
                        FROM fixtures f
                        WHERE f.league_id = ? AND f.home_team_id = ? AND f.status = 'complete'
                        ORDER BY f.date_unix DESC
                        LIMIT 5
                    """, (league_id, team_id))
                    
                    form_home_results = cursor.fetchall()
                    form_home = ''.join([r[0] for r in reversed(form_home_results)]) if form_home_results else ""
                    
                    # Gera form away
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN f.away_goal_count > f.home_goal_count THEN 'W'
                                WHEN f.away_goal_count = f.home_goal_count THEN 'D'
                                ELSE 'L'
                            END as result
                        FROM fixtures f
                        WHERE f.league_id = ? AND f.away_team_id = ? AND f.status = 'complete'
                        ORDER BY f.date_unix DESC
                        LIMIT 5
                    """, (league_id, team_id))
                    
                    form_away_results = cursor.fetchall()
                    form_away = ''.join([r[0] for r in reversed(form_away_results)]) if form_away_results else ""
                    
                    # Determina descrição baseada na posição
                    if rank <= 4:
                        description = "Copa Libertadores"
                    elif rank <= 6:
                        description = "Copa Sul-Americana"
                    elif rank >= 17:
                        description = "Rebaixamento"
                    else:
                        description = ""
                    
                    team_data = {
                        "rank": rank,
                        "team": {
                            "id": team_id,
                            "name": team_name,
                            "logo": team_logo or ""
                        },
                        "points": points,
                        "goalsDiff": goals_diff,
                        "group": f"{league_name} 2025",
                        "status": "same",
                        "description": description,
                        "all": {
                            "played": played,
                            "win": wins,
                            "draw": draws,
                            "lose": losses,
                            "goals": {
                                "for": goals_for,
                                "against": goals_against
                            },
                            "form": form,
                            "btts_matches": general_stats[0] or 0,
                            "avg_corners_per_game": round(general_stats[5] or 0, 2),
                            "aproveitamento": aproveitamento,
                            "over_2_5_goals": general_stats[1] or 0,
                            "over_0_5_ht": general_stats[3] or 0,
                            "over_0_5_ft": general_stats[4] or 0,
                            "clean_sheets": general_stats[2] or 0,
                        },
                        "home": {
                            "played": home_stats[0] or 0,
                            "win": home_stats[1] or 0,
                            "draw": home_stats[2] or 0,
                            "lose": home_stats[3] or 0,
                            "goals": {
                                "for": home_stats[4] or 0,
                                "against": home_stats[5] or 0
                            },
                            "form_home": form_home,
                            "avg_corners_home_per_game": round(home_stats[11] or 0, 2),
                            "aproveitamento_home": aproveitamento_home,
                            "btts_home_matches": home_stats[6] or 0,
                            "over_2_5_goals_home": home_stats[7] or 0,
                            "over_0_5_ht_home": home_stats[9] or 0,
                            "over_0_5_ft_home": home_stats[10] or 0,
                            "clean_sheets_home": home_stats[8] or 0,
                        },
                        "away": {
                            "played": away_stats[0] or 0,
                            "win": away_stats[1] or 0,
                            "draw": away_stats[2] or 0,
                            "lose": away_stats[3] or 0,
                            "goals": {
                                "for": away_stats[4] or 0,
                                "against": away_stats[5] or 0
                            },
                            "form_visitor": form_away,
                            "btts_away_matches": away_stats[6] or 0,
                            "avg_corners_away_per_game": round(away_stats[11] or 0, 2),
                            "aproveitamento_away": aproveitamento_away,
                            "over_2_5_goals_away": away_stats[7] or 0,
                            "over_0_5_ht_away": away_stats[9] or 0,
                            "over_0_5_ft_away": away_stats[10] or 0,
                            "clean_sheets_away": away_stats[8] or 0
                        },
                        "update": "2025-09-23T00:00:00+00:00",
                    }
                    standings.append(team_data)
                
                # Obtém artilharia do banco de dados
                artilharia = self.get_league_top_scorers_from_db(league_id)
                
                # Estrutura final no formato do example.json
                export_data = {
                    "standings": {
                        league_name.lower().replace(" ", "_"): standings
                    },
                    "artilharia": {
                        league_name.lower().replace(" ", "_"): artilharia
                    }
                }
                
                # Salva o arquivo
                if not output_file:
                    output_file = f"{league_name.lower().replace(' ', '_')}_data.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Dados exportados para {output_file}")
                logger.info(f"   📊 {len(standings)} times na tabela de classificação")
                logger.info(f"   🏆 Liga: {league_name} ({country})")
                
                # Envia para GitHub se configurado
                if GITHUB_TOKEN:
                    salvar_em_github(export_data, output_file)
                
                return export_data
                
        except Exception as e:
            logger.error(f"Erro ao exportar dados da liga {league_id}: {e}")
            return None

def salvar_em_github(json_data, filename):
    """Salva dados no GitHub via API REST"""
    if not GITHUB_TOKEN:
        logger.warning("⚠️ Token do GitHub não configurado, pulando upload")
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

def main():
    """Função principal"""
    start_time = time.time()
    
    try:
        logger.info("🎯 Iniciando sistema de coleta de dados de futebol - FootyStats API")
        logger.info("=" * 60)
        
        # Coletar dados
        logger.info("📊 FASE 1: Coleta de dados das ligas")
        collector = FootballDataCollector()
        collector.collect_all_data()
        logger.info("✅ FASE 1 concluída: Coleta de dados finalizada!")
        
        # Exportar dados para JSON
        logger.info("📊 FASE 2: Exportação de dados para JSON")
        if collector.leagues:
            for league in collector.leagues:  # Exporta TODAS as ligas
                logger.info(f"📤 Exportando dados da liga: {league.name} {league.season_year}")
                collector.export_league_data_to_json(league.id)
        logger.info("✅ FASE 2 concluída: Exportação de dados finalizada!")
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info("🎯 PROCESSAMENTO CONCLUÍDO!")
        logger.info(f"   ⏱️  Tempo total de execução: {duration:.2f} segundos")
        
    except Exception as e:
        logger.error(f"❌ Erro crítico no processamento: {e}")
        logger.error(f"🔍 Detalhes do erro: {type(e).__name__}: {str(e)}")
        raise

if __name__ == "__main__":
    main()
