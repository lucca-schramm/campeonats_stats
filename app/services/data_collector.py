"""Serviço de coleta de dados da API FootyStats"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.league import League
from app.models.team import Team
from app.models.fixture import Fixture
from app.models.player import Player
from app.models.team_statistics import TeamStatistics
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LeagueConfig:
    """Configuração de uma liga"""
    id: int
    name: str
    country: str
    season_id: int
    season_year: int


class FootyStatsAPIClient:
    """Cliente simplificado para consumir a API FootyStats"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.timeout = 30
        self.last_request_time = 0
        self.min_interval = 0.5  # 2 req/s
        self.api_base_url = settings.API_BASE_URL
    
    def make_request(self, endpoint: str, params: Optional[Dict] = None, max_retries: int = 2) -> Dict:
        """Faz requisição com rate limiting simples"""
        if params is None:
            params = {}
        
        params['key'] = self.api_key
        url = f"{self.api_base_url}/{endpoint}"
        
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Requisição {attempt + 1}/{max_retries}: {endpoint}")
                safe_params = {k: (v[:10] + '...' if k == 'key' and len(str(v)) > 10 else v) for k, v in params.items()}
                logger.info(f"Params: {safe_params}")
                response = self.session.get(url, params=params, timeout=30)
                logger.info(f"Status code: {response.status_code}")
                
                if response.status_code == 429:
                    wait = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit atingido. Aguardando {wait}s...")
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                    return {}
                
                if response.status_code != 200:
                    error_text = response.text[:500] if hasattr(response, 'text') else str(response.content[:500])
                    logger.error(f"Status code {response.status_code}: {error_text}")
                    return {}
                
                response.raise_for_status()
                result = response.json()
                logger.info(f"Resposta recebida com sucesso (tipo: {type(result)})")
                return result
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro na requisição {url} (tentativa {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.info(f"Aguardando {wait}s antes de retry...")
                    time.sleep(wait)
                    continue
                return {}
        
        return {}
    
    def get_available_leagues(self) -> List[Dict]:
        """Obtém todas as ligas disponíveis"""
        params = {"chosen_leagues_only": "true"}
        logger.info(f"Tentando obter ligas escolhidas...")
        data = self.make_request("league-list", params)
        
        if not data:
            logger.warning("Nenhuma liga escolhida encontrada. Tentando todas as ligas...")
            params = {}
            data = self.make_request("league-list", params)
        
        if not data:
            logger.error("ERRO: API não retornou dados!")
            return []
        
        logger.info(f"Resposta recebida: tipo={type(data)}")
        
        leagues = []
        if isinstance(data, dict):
            if "data" in data:
                leagues = data["data"]
            elif "leagues" in data:
                leagues = data["leagues"]
            elif "results" in data:
                leagues = data["results"]
            else:
                logger.warning(f"Dict sem campo conhecido. Keys: {list(data.keys())}")
                for value in data.values():
                    if isinstance(value, list):
                        leagues = value
                        break
        elif isinstance(data, list):
            leagues = data
        else:
            logger.error(f"Formato de resposta inesperado: {type(data)}")
            return []
        
        logger.info(f"Total de ligas extraídas: {len(leagues)}")
        if len(leagues) > 0:
            logger.info(f"Primeira liga exemplo: {list(leagues[0].keys()) if isinstance(leagues[0], dict) else 'N/A'}")
        
        return leagues
    
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
            
            pager = data.get("pager", {})
            current_page = pager.get("current_page", page)
            max_page = pager.get("max_page", 1)
            
            if current_page % 5 == 0 or current_page == max_page:
                logger.info(f"📄 Página {current_page}/{max_page}: {len(players)} jogadores coletados")
            
            if current_page >= max_page:
                break
                
            page += 1
            time.sleep(0.2)
        
        total_results = data.get("pager", {}).get("total_results", len(all_players)) if data else len(all_players)
        logger.info(f"✅ Total de jogadores coletados: {len(all_players)}/{total_results}")
        
        return all_players


class FootballDataCollector:
    """Coletor principal de dados de futebol - PostgreSQL"""
    
    def __init__(self):
        api_key = settings.FOOTYSTATS_API_KEY
        if not api_key:
            raise ValueError("FOOTYSTATS_API_KEY não configurada no arquivo .env")
        self.api = FootyStatsAPIClient(api_key)
        self.leagues = []
    
    def get_db_session(self) -> Session:
        """Retorna uma sessão do banco de dados PostgreSQL"""
        return SessionLocal()
    
    def get_current_year(self) -> int:
        """Retorna o ano atual"""
        return datetime.now().year
    
    def get_latest_season(self, seasons: List[Dict]) -> Dict:
        """Retorna a temporada mais recente disponível"""
        if not seasons:
            return None
        
        sorted_seasons = sorted(seasons, key=lambda x: x.get("year", 0), reverse=True)
        return sorted_seasons[0]
    
    def get_league_id_from_database(self, season_id: int, league_name: str, country: str) -> int:
        """Busca o league_id no banco ou gera um novo"""
        db = self.get_db_session()
        try:
            existing_league = db.query(League).filter(League.season_id == season_id).first()
            if existing_league:
                return existing_league.id
            
            league_id = abs(hash(f"{league_name}_{country}_{season_id}")) % 1000000
            return league_id if league_id > 0 else 1
        except Exception as e:
            logger.error(f"Erro ao buscar league_id: {e}")
            return abs(hash(f"{league_name}_{country}_{season_id}")) % 1000000 or 1
        finally:
            db.close()
    
    def load_leagues_from_api(self):
        """Carrega as ligas escolhidas da API"""
        logger.info("Obtendo ligas escolhidas da API FootyStats...")
        
        api_leagues = self.api.get_available_leagues()
        
        logger.info(f"Resposta da API: {type(api_leagues)}, tamanho: {len(api_leagues) if api_leagues else 0}")
        
        if not api_leagues:
            logger.error("ERRO: Nenhuma liga encontrada na API!")
            logger.error("Verifique:")
            logger.error("1. FOOTYSTATS_API_KEY está configurada no .env?")
            logger.error("2. API_BASE_URL está correto?")
            logger.error("3. Você configurou ligas escolhidas na API FootyStats?")
            return []
        
        logger.info(f"Encontradas {len(api_leagues)} ligas na API")
        
        for league_data in api_leagues:
            try:
                league_name = league_data.get("name", "")
                country = league_data.get("country", "")
                
                seasons = league_data.get("season", [])
                latest_season = self.get_latest_season(seasons)
                
                if not latest_season:
                    logger.warning(f"❌ Nenhuma temporada encontrada para liga: {league_name}")
                    continue
                
                season_id = latest_season.get("id")
                season_year = latest_season.get("year")
                
                if season_id and season_year:
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
    
    def save_league(self, league_data: Dict) -> int:
        """Salva uma liga no banco de dados PostgreSQL"""
        db = self.get_db_session()
        try:
            league_id = league_data["id"]
            logger.info(f"Salvando liga: ID={league_id}, Nome={league_data.get('name')}")
            
            league = db.query(League).filter(League.id == league_id).first()
            
            if league:
                # Atualiza registro existente
                logger.debug(f"Liga {league_id} já existe, atualizando...")
                league.name = league_data["name"]
                league.country = league_data["country"]
                league.image = league_data.get("image")
                league.season_id = league_data["season_id"]
                league.season_year = league_data["season_year"]
            else:
                # Cria novo registro
                logger.info(f"Criando nova liga: {league_data.get('name')}")
                league = League(
                    id=league_id,
                    name=league_data["name"],
                    country=league_data["country"],
                    image=league_data.get("image"),
                    season_id=league_data["season_id"],
                    season_year=league_data["season_year"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(league)
            
            db.commit()
            logger.info(f"✓ Liga {league_id} salva com sucesso")
            return league_id
        except Exception as e:
            db.rollback()
            logger.error(f"✗ Erro ao salvar liga {league_data.get('name', 'N/A')}: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    def save_team(self, team_data: Dict, league_id: int, season_id: int) -> int:
        """Salva um time no banco de dados PostgreSQL"""
        db = self.get_db_session()
        try:
            team_id = team_data.get("id")
            team_name = team_data.get("name", "").strip()
            
            if not team_id:
                logger.warning(f"ID do time não encontrado: {team_data}")
                return None
            
            if not team_name:
                logger.warning(f"Nome do time vazio para ID {team_id}")
                return None
            
            team = db.query(Team).filter(
                Team.id == team_id,
                Team.league_id == league_id,
                Team.season_id == season_id
            ).first()
            
            if team:
                team.name = team_name
                team.clean_name = team_data.get("cleanName")
                team.english_name = team_data.get("english_name")
                team.short_hand = team_data.get("shortHand")
                team.country = team_data.get("country")
                team.image = team_data.get("image")
                team.url = team_data.get("url")
                team.table_position = team_data.get("table_position")
                team.performance_rank = team_data.get("performance_rank")
                logger.debug(f"Time atualizado: ID {team_id} - {team_name}")
            else:
                team = Team(
                    id=team_id,
                    name=team_name,
                    clean_name=team_data.get("cleanName"),
                    english_name=team_data.get("english_name"),
                    short_hand=team_data.get("shortHand"),
                    country=team_data.get("country"),
                    image=team_data.get("image"),
                    url=team_data.get("url"),
                    table_position=team_data.get("table_position"),
                    performance_rank=team_data.get("performance_rank"),
                    league_id=league_id,
                    season_id=season_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(team)
                logger.debug(f"Time salvo: ID {team_id} - {team_name}")
            
            db.commit()
            return team_data["id"]
        except IntegrityError:
            db.rollback()
            logger.warning(f"Erro de integridade ao salvar time {team_id}, tentando atualizar...")
            # Tenta atualizar se já existe
            try:
                team = db.query(Team).filter(
                    Team.id == team_id,
                    Team.league_id == league_id,
                    Team.season_id == season_id
                ).first()
                if team:
                    db.commit()
                    return team_data["id"]
            except:
                pass
            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar time: {e}")
            return None
        finally:
            db.close()
    
    def save_fixture(self, fixture_data: Dict, league_id: int, season_id: int) -> int:
        """Salva uma partida no banco de dados PostgreSQL adaptada para FootyStats"""
        db = self.get_db_session()
        try:
            fixture_id = fixture_data.get("id")
            home_team_id = fixture_data.get("homeID")
            away_team_id = fixture_data.get("awayID")
            home_team_name = fixture_data.get("home_name", "Unknown")
            away_team_name = fixture_data.get("away_name", "Unknown")
            
            if not fixture_id:
                logger.warning(f"ID da partida não encontrado: {fixture_data}")
                return None
            
            if not home_team_id or not away_team_id:
                logger.warning(f"IDs dos times não encontrados para partida {fixture_id}")
                return None
            
            fixture = db.query(Fixture).filter(Fixture.id == fixture_id).first()
            
            if fixture:
                fixture.league_id = league_id
                fixture.season_id = season_id
                fixture.home_team_id = home_team_id
                fixture.away_team_id = away_team_id
                fixture.home_team_name = home_team_name
                fixture.away_team_name = away_team_name
                fixture.status = fixture_data.get("status", "Unknown")
                fixture.date_unix = fixture_data.get("date_unix")
                fixture.home_goal_count = fixture_data.get("homeGoalCount", 0)
                fixture.away_goal_count = fixture_data.get("awayGoalCount", 0)
                fixture.total_goal_count = fixture_data.get("totalGoalCount", 0)
                fixture.home_corners = fixture_data.get("team_a_corners", 0)
                fixture.away_corners = fixture_data.get("team_b_corners", 0)
                fixture.home_possession = fixture_data.get("team_a_possession", 0)
                fixture.away_possession = fixture_data.get("team_b_possession", 0)
                fixture.home_shots = fixture_data.get("team_a_shots", 0)
                fixture.away_shots = fixture_data.get("team_b_shots", 0)
                fixture.home_xg = fixture_data.get("team_a_xg")
                fixture.away_xg = fixture_data.get("team_b_xg")
                fixture.home_yellow_cards = fixture_data.get("team_a_yellow_cards", 0)
                fixture.away_yellow_cards = fixture_data.get("team_b_yellow_cards", 0)
                fixture.home_red_cards = fixture_data.get("team_a_red_cards", 0)
                fixture.away_red_cards = fixture_data.get("team_b_red_cards", 0)
                fixture.over05 = fixture_data.get("over05", False)
                fixture.over15 = fixture_data.get("over15", False)
                fixture.over25 = fixture_data.get("over25", False)
                fixture.over35 = fixture_data.get("over35", False)
                fixture.btts = fixture_data.get("btts", False)
                fixture.stadium_name = fixture_data.get("stadium_name")
                fixture.round = fixture_data.get("round") or fixture_data.get("Round")
                fixture.phase = fixture_data.get("phase") or fixture_data.get("Phase")
                fixture.stage = fixture_data.get("stage") or fixture_data.get("Stage")
                fixture.group_name = fixture_data.get("group") or fixture_data.get("Group") or fixture_data.get("group_name")
                logger.debug(f"Partida atualizada: ID {fixture_id} - {home_team_name} vs {away_team_name}")
            else:
                fixture = Fixture(
                    id=fixture_id,
                    league_id=league_id,
                    season_id=season_id,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_team_name=home_team_name,
                    away_team_name=away_team_name,
                    status=fixture_data.get("status", "Unknown"),
                    date_unix=fixture_data.get("date_unix"),
                    home_goal_count=fixture_data.get("homeGoalCount", 0),
                    away_goal_count=fixture_data.get("awayGoalCount", 0),
                    total_goal_count=fixture_data.get("totalGoalCount", 0),
                    home_corners=fixture_data.get("team_a_corners", 0),
                    away_corners=fixture_data.get("team_b_corners", 0),
                    home_possession=fixture_data.get("team_a_possession", 0),
                    away_possession=fixture_data.get("team_b_possession", 0),
                    home_shots=fixture_data.get("team_a_shots", 0),
                    away_shots=fixture_data.get("team_b_shots", 0),
                    home_xg=fixture_data.get("team_a_xg"),
                    away_xg=fixture_data.get("team_b_xg"),
                    home_yellow_cards=fixture_data.get("team_a_yellow_cards", 0),
                    away_yellow_cards=fixture_data.get("team_b_yellow_cards", 0),
                    home_red_cards=fixture_data.get("team_a_red_cards", 0),
                    away_red_cards=fixture_data.get("team_b_red_cards", 0),
                    over05=fixture_data.get("over05", False),
                    over15=fixture_data.get("over15", False),
                    over25=fixture_data.get("over25", False),
                    over35=fixture_data.get("over35", False),
                    btts=fixture_data.get("btts", False),
                    stadium_name=fixture_data.get("stadium_name"),
                    round=fixture_data.get("round") or fixture_data.get("Round"),
                    phase=fixture_data.get("phase") or fixture_data.get("Phase"),
                    stage=fixture_data.get("stage") or fixture_data.get("Stage"),
                    group_name=fixture_data.get("group") or fixture_data.get("Group") or fixture_data.get("group_name"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(fixture)
                logger.debug(f"Partida salva: ID {fixture_id} - {home_team_name} vs {away_team_name}")
            
            db.commit()
            return fixture_id
            
        except IntegrityError:
            db.rollback()
            logger.warning(f"Erro de integridade ao salvar fixture {fixture_id}, tentando atualizar...")
            try:
                fixture = db.query(Fixture).filter(Fixture.id == fixture_id).first()
                if fixture:
                    db.commit()
                    return fixture_id
            except:
                pass
            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar partida: {e}")
            return None
        finally:
            db.close()
    
    def save_team_statistics(self, team_stats: Dict, league_id: int, season_id: int, season_year: int) -> bool:
        """Salva estatísticas de um time no banco de dados PostgreSQL"""
        db = self.get_db_session()
        try:
            team_id = team_stats.get("team_id") or team_stats.get("id")
            if not team_id:
                logger.warning(f"ID do time não encontrado: {team_stats}")
                return False
            
            stats = db.query(TeamStatistics).filter(
                TeamStatistics.team_id == team_id,
                TeamStatistics.league_id == league_id,
                TeamStatistics.season_id == season_id
            ).first()
            
            if stats:
                stats.season_year = season_year
                stats.matches_played = team_stats.get("matches_played", 0)
                stats.wins = team_stats.get("wins", 0)
                stats.draws = team_stats.get("draws", 0)
                stats.losses = team_stats.get("losses", 0)
                stats.goals_for = team_stats.get("goals_for", 0)
                stats.goals_against = team_stats.get("goals_against", 0)
                stats.points = team_stats.get("points", 0)
                stats.rank = team_stats.get("rank", 0)
                stats.position = team_stats.get("position", 0)
            else:
                stats = TeamStatistics(
                    team_id=team_id,
                    league_id=league_id,
                    season_id=season_id,
                    season_year=season_year,
                    matches_played=team_stats.get("matches_played", 0),
                    wins=team_stats.get("wins", 0),
                    draws=team_stats.get("draws", 0),
                    losses=team_stats.get("losses", 0),
                    goals_for=team_stats.get("goals_for", 0),
                    goals_against=team_stats.get("goals_against", 0),
                    points=team_stats.get("points", 0),
                    rank=team_stats.get("rank", 0),
                    position=team_stats.get("position", 0),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(stats)
            
            db.commit()
            logger.debug(f"Estatísticas do time {team_id} salvas")
            return True
                
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar estatísticas do time: {e}")
            return False
        finally:
            db.close()
    
    def save_player(self, player_data: Dict, team_id: int, league_id: int, season_id: int) -> int:
        """Salva dados de um jogador no banco de dados PostgreSQL"""
        db = self.get_db_session()
        try:
            team = db.query(Team).filter(Team.id == team_id).first()
            team_name = team.name if team else "Unknown"
            
            player_name = player_data.get("name", "").strip()
            if not player_name or player_name == "N/A" or player_name == "Unknown":
                logger.debug(f"⏭️  Jogador sem nome válido pulado para team_id {team_id}: '{player_name}'")
                return None
            
            player = db.query(Player).filter(
                Player.name == player_name,
                Player.team_id == team_id,
                Player.season_id == season_id
            ).first()
            
            if player:
                player.team_name = team_name
                player.position = player_data.get("position", "")
                player.goals = player_data.get("goals", 0) or 0
                player.assists = player_data.get("assists", 0) or 0
                player.matches_played = player_data.get("matches_played", 0) or 0
                player.league_id = league_id
                player.age = player_data.get("age")
                player.height = player_data.get("height")
                player.weight = player_data.get("weight")
                player.url = player_data.get("url")
                player.minutes_played = player_data.get("minutes_played", 0) or 0
                player.clean_sheets = player_data.get("clean_sheets", 0) or 0
                player.yellow_cards = player_data.get("yellow_cards", 0) or 0
                player.red_cards = player_data.get("red_cards", 0) or 0
                logger.debug(f"Jogador atualizado: {player_name} - {team_name}")
                db.commit()
                return player.id
            else:
                player = Player(
                    name=player_name,
                    team_id=team_id,
                    team_name=team_name,
                    position=player_data.get("position", ""),
                    goals=player_data.get("goals", 0) or 0,
                    assists=player_data.get("assists", 0) or 0,
                    matches_played=player_data.get("matches_played", 0) or 0,
                    league_id=league_id,
                    season_id=season_id,
                    age=player_data.get("age"),
                    height=player_data.get("height"),
                    weight=player_data.get("weight"),
                    url=player_data.get("url"),
                    minutes_played=player_data.get("minutes_played", 0) or 0,
                    clean_sheets=player_data.get("clean_sheets", 0) or 0,
                    yellow_cards=player_data.get("yellow_cards", 0) or 0,
                    red_cards=player_data.get("red_cards", 0) or 0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(player)
                db.commit()
                logger.debug(f"Jogador salvo: {player_name} - {team_name}")
                return player.id
                
        except IntegrityError:
            db.rollback()
            logger.warning(f"Erro de integridade ao salvar jogador {player_name}, tentando atualizar...")
            try:
                player = db.query(Player).filter(
                    Player.name == player_name,
                    Player.team_id == team_id,
                    Player.season_id == season_id
                ).first()
                if player:
                    db.commit()
                    return player.id
            except:
                pass
            return None
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar jogador: {e}")
            return None
        finally:
            db.close()
    
    
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
            
            players_by_team = {}
            for player in players_list:
                team_id = player.get("club_team_id")
                if team_id and team_id != -1:
                    if team_id not in players_by_team:
                        players_by_team[team_id] = []
                    players_by_team[team_id].append(player)
            
            logger.info(f"📊 Jogadores distribuídos em {len(players_by_team)} times")
            
            total_saved = 0
            batch_size = 200
            
            all_players_data = []
            for team_id, team_players in players_by_team.items():
                logger.info(f"💾 Processando {len(team_players)} jogadores do time {team_id}")
                
                for player in team_players:
                    player_name = (player.get("full_name") or 
                                 player.get("name") or 
                                 player.get("player_name") or 
                                 f"Jogador_{player.get('id', 'Unknown')}")
                    
                    if not player_name or player_name.strip() == "":
                        logger.debug(f"⏭️  Jogador sem nome válido pulado: {player}")
                        continue
                    
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
            
            for i in range(0, len(all_players_data), batch_size):
                batch = all_players_data[i:i + batch_size]
                logger.info(f"💾 Salvando lote de {len(batch)} jogadores...")
                
                for player_data, team_id, league_id, season_id in batch:
                    saved_player_id = self.save_player(player_data, team_id, league_id, season_id)
                    if saved_player_id:
                        total_saved += 1
            
            logger.info(f"✅ {total_saved} jogadores salvos com sucesso!")
                
        except Exception as e:
            logger.error(f"❌ Erro ao coletar dados de jogadores: {e}")
    
    def get_league_top_scorers_from_db(self, league_id: int) -> List[Dict]:
        """Obtém artilharia do banco de dados PostgreSQL"""
        db = self.get_db_session()
        try:
            results = db.query(
                Player.name,
                Player.team_name,
                Player.position,
                Player.goals,
                Player.assists,
                Player.matches_played,
                Team.image.label('team_logo'),
                Player.url
            ).join(
                Team, Player.team_id == Team.id, isouter=True
            ).filter(
                Player.league_id == league_id,
                Player.goals > 0
            ).group_by(
                Player.name, Player.team_name, Player.position, Player.goals,
                Player.assists, Player.matches_played, Team.image, Player.url
            ).order_by(
                Player.goals.desc(), Player.assists.desc()
            ).limit(20).all()
            
            scorers = []
            for row in results:
                name, team_name, position, goals, assists, matches, team_logo, player_url = row
                
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
        finally:
            db.close()

    def _generate_player_photo_url(self, player_name: str, player_url: str = None) -> str:
        """Gera URL da foto do jogador incluindo nacionalidade extraída da URL"""
        try:
            if not player_url:
                return f"https://cdn.footystats.org/img/players/-{player_name.lower().replace(' ', '-')}.png"
            
            url_parts = player_url.split('/')
            if len(url_parts) >= 6 and url_parts[3] == 'players':
                nationality = url_parts[4]
                url_player_name = url_parts[5]
                return f"https://cdn.footystats.org/img/players/{nationality}-{url_player_name}.png"
            else:
                return f"https://cdn.footystats.org/img/players/-{player_name.lower().replace(' ', '-')}.png"
                
        except Exception as e:
            logger.warning(f"Erro ao gerar URL da foto para {player_name}: {e}")
            return f"https://cdn.footystats.org/img/players/-{player_name.lower().replace(' ', '-')}.png"

    def collect_league_data(self, league_config: LeagueConfig):
        """Coleta todos os dados de uma liga"""
        logger.info(f"🏆 Iniciando coleta da liga: {league_config.name} {league_config.season_year} (Season ID: {league_config.season_id})")
        
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
        
        teams = self.api.get_league_teams(league_config.season_id)
        logger.info(f"👥 Encontrados {len(teams)} times na liga")
        
        teams_processed = set()
        for team in teams:
            if team.get("id") and team["id"] not in teams_processed:
                self.save_team(team, league_config.id, league_config.season_id)
                logger.debug(f"✅ Time processado: {team.get('name', 'N/A')}")
                teams_processed.add(team["id"])
        
        fixtures = self.api.get_league_matches(league_config.season_id)
        logger.info(f"📋 Encontradas {len(fixtures)} partidas na API")
        
        fixtures_processed = 0
        
        for fixture in fixtures:
            saved_fixture_id = self.save_fixture(fixture, league_config.id, league_config.season_id)
            if saved_fixture_id:
                fixtures_processed += 1
        
        logger.info("👥 Coletando dados de jogadores...")
        self.collect_players_data(league_config)
        
        logger.info("📊 Construindo tabela de classificação a partir dos dados coletados...")
        self.build_league_table_from_matches(league_config.id, league_config.season_id, league_config.season_year)
        
        logger.info(f"Coleta concluída: {fixtures_processed} partidas, {len(teams_processed)} times")
    
    def collect_all_data(self):
        """Coleta dados de todas as ligas configuradas"""
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("INICIANDO COLETA DE DADOS")
        logger.info("=" * 60)
        
        try:
            self.load_leagues_from_api()
        except Exception as e:
            logger.error(f"ERRO ao carregar ligas da API: {e}", exc_info=True)
            raise
        
        logger.info(f"Total de ligas carregadas da API: {len(self.leagues)}")
        
        if len(self.leagues) == 0:
            logger.error("=" * 60)
            logger.error("ERRO CRÍTICO: Nenhuma liga foi carregada!")
            logger.error("A coleta não pode continuar sem ligas.")
            logger.error("=" * 60)
            raise ValueError("Nenhuma liga encontrada para coletar. Verifique: 1) API key válida, 2) Ligas configuradas na API FootyStats")
        
        successful = 0
        failed = 0
        
        for idx, league_config in enumerate(self.leagues, 1):
            try:
                logger.info(f"[{idx}/{len(self.leagues)}] Processando liga: {league_config.name}")
                self.collect_league_data(league_config)
                successful += 1
                logger.info(f"✓ Liga {league_config.name} processada com sucesso")
            except Exception as e:
                failed += 1
                logger.error(f"✗ Erro ao processar liga {league_config.name}: {e}", exc_info=True)
        
        duration = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"COLETA CONCLUÍDA: {successful} sucesso, {failed} falhas, {duration:.2f}s")
        logger.info("=" * 60)
        
        if successful == 0:
            raise ValueError(f"Todas as {len(self.leagues)} ligas falharam na coleta. Verifique logs para detalhes.")
    
    def build_league_table_from_matches(self, league_id: int, season_id: int, season_year: int = None):
        """Constrói tabela de classificação a partir dos dados de partidas coletados - PostgreSQL"""
        db = self.get_db_session()
        try:
            teams = db.query(Team.id, Team.name).filter(Team.season_id == season_id).all()
            
            if not teams:
                logger.warning(f"Nenhum time encontrado para liga {league_id}")
                return
            
            for team_id, team_name in teams:
                home_query = db.query(
                    func.count(Fixture.id).label('matches'),
                    func.sum(case((Fixture.home_goal_count > Fixture.away_goal_count, 1), else_=0)).label('wins'),
                    func.sum(case((Fixture.home_goal_count == Fixture.away_goal_count, 1), else_=0)).label('draws'),
                    func.sum(case((Fixture.home_goal_count < Fixture.away_goal_count, 1), else_=0)).label('losses'),
                    func.sum(Fixture.home_goal_count).label('goals_for'),
                    func.sum(Fixture.away_goal_count).label('goals_against')
                ).filter(
                    Fixture.season_id == season_id,
                    Fixture.home_team_id == team_id,
                    Fixture.status == 'complete'
                ).first()
                
                home_stats = (home_query.matches or 0, home_query.wins or 0, home_query.draws or 0,
                             home_query.losses or 0, home_query.goals_for or 0, home_query.goals_against or 0)
                
                away_query = db.query(
                    func.count(Fixture.id).label('matches'),
                    func.sum(case((Fixture.away_goal_count > Fixture.home_goal_count, 1), else_=0)).label('wins'),
                    func.sum(case((Fixture.away_goal_count == Fixture.home_goal_count, 1), else_=0)).label('draws'),
                    func.sum(case((Fixture.away_goal_count < Fixture.home_goal_count, 1), else_=0)).label('losses'),
                    func.sum(Fixture.away_goal_count).label('goals_for'),
                    func.sum(Fixture.home_goal_count).label('goals_against')
                ).filter(
                    Fixture.season_id == season_id,
                    Fixture.away_team_id == team_id,
                    Fixture.status == 'complete'
                ).first()
                
                away_stats = (away_query.matches or 0, away_query.wins or 0, away_query.draws or 0,
                             away_query.losses or 0, away_query.goals_for or 0, away_query.goals_against or 0)
                
                total_matches = home_stats[0] + away_stats[0]
                total_wins = home_stats[1] + away_stats[1]
                total_draws = home_stats[2] + away_stats[2]
                total_losses = home_stats[3] + away_stats[3]
                total_goals_for = home_stats[4] + away_stats[4]
                total_goals_against = home_stats[5] + away_stats[5]
                total_points = (total_wins * 3) + (total_draws * 1)
                
                stats = db.query(TeamStatistics).filter(
                    TeamStatistics.team_id == team_id,
                    TeamStatistics.league_id == league_id,
                    TeamStatistics.season_id == season_id
                ).first()
                
                if stats:
                    stats.season_year = season_year or 2025
                    stats.matches_played = total_matches
                    stats.wins = total_wins
                    stats.draws = total_draws
                    stats.losses = total_losses
                    stats.goals_for = total_goals_for
                    stats.goals_against = total_goals_against
                    stats.points = total_points
                    stats.rank = 0
                    stats.position = 0
                else:
                    stats = TeamStatistics(
                        team_id=team_id,
                        league_id=league_id,
                        season_id=season_id,
                        season_year=season_year or 2025,
                        matches_played=total_matches,
                        wins=total_wins,
                        draws=total_draws,
                        losses=total_losses,
                        goals_for=total_goals_for,
                        goals_against=total_goals_against,
                        points=total_points,
                        rank=0,
                        position=0,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(stats)

            stats_list = db.query(TeamStatistics).filter(
                TeamStatistics.league_id == league_id,
                TeamStatistics.season_id == season_id
            ).all()

            team_rows = {}
            for stat in stats_list:
                team_rows[stat.team_id] = {
                    "team_id": stat.team_id,
                    "points": stat.points or 0,
                    "wins": stat.wins or 0,
                    "gd": (stat.goals_for or 0) - (stat.goals_against or 0),
                    "gf": stat.goals_for or 0,
                    "h2h_points": 0,
                    "red_cards": 0,
                    "yellow_cards": 0,
                }

            if team_rows:
                team_ids = list(team_rows.keys())

                for team_id in team_ids:
                    red_cards_home = db.query(func.sum(Fixture.home_red_cards)).filter(
                        Fixture.league_id == league_id,
                        Fixture.season_id == season_id,
                        Fixture.home_team_id == team_id,
                        Fixture.status == 'complete'
                    ).scalar() or 0
                    
                    red_cards_away = db.query(func.sum(Fixture.away_red_cards)).filter(
                        Fixture.league_id == league_id,
                        Fixture.season_id == season_id,
                        Fixture.away_team_id == team_id,
                        Fixture.status == 'complete'
                    ).scalar() or 0
                    
                    # Yellow cards
                    yellow_cards_home = db.query(func.sum(Fixture.home_yellow_cards)).filter(
                        Fixture.league_id == league_id,
                        Fixture.season_id == season_id,
                        Fixture.home_team_id == team_id,
                        Fixture.status == 'complete'
                    ).scalar() or 0
                    
                    yellow_cards_away = db.query(func.sum(Fixture.away_yellow_cards)).filter(
                        Fixture.league_id == league_id,
                        Fixture.season_id == season_id,
                        Fixture.away_team_id == team_id,
                        Fixture.status == 'complete'
                    ).scalar() or 0
                    
                    team_rows[team_id]["red_cards"] = red_cards_home + red_cards_away
                    team_rows[team_id]["yellow_cards"] = yellow_cards_home + yellow_cards_away

                from collections import defaultdict
                groups = defaultdict(list)
                for t in team_rows.values():
                    groups[(t["points"], t["wins"], t["gd"], t["gf"])].append(t["team_id"])

                for key, tied_team_ids in groups.items():
                    if len(tied_team_ids) <= 1:
                        continue
                    
                    for team_id in tied_team_ids:
                        h2h_points = 0
                        home_fixtures = db.query(Fixture).filter(
                            Fixture.league_id == league_id,
                            Fixture.season_id == season_id,
                            Fixture.home_team_id == team_id,
                            Fixture.away_team_id.in_(tied_team_ids),
                            Fixture.status == 'complete'
                        ).all()
                        
                        for fixture in home_fixtures:
                            if fixture.home_goal_count > fixture.away_goal_count:
                                h2h_points += 3
                            elif fixture.home_goal_count == fixture.away_goal_count:
                                h2h_points += 1
                        
                        away_fixtures = db.query(Fixture).filter(
                            Fixture.league_id == league_id,
                            Fixture.season_id == season_id,
                            Fixture.away_team_id == team_id,
                            Fixture.home_team_id.in_(tied_team_ids),
                            Fixture.status == 'complete'
                        ).all()
                        
                        for fixture in away_fixtures:
                            if fixture.away_goal_count > fixture.home_goal_count:
                                h2h_points += 3
                            elif fixture.away_goal_count == fixture.home_goal_count:
                                h2h_points += 1
                        
                        team_rows[team_id]["h2h_points"] = h2h_points

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

                for idx, t in enumerate(sorted_teams, start=1):
                    stat = db.query(TeamStatistics).filter(
                        TeamStatistics.league_id == league_id,
                        TeamStatistics.season_id == season_id,
                        TeamStatistics.team_id == t["team_id"]
                    ).first()
                    if stat:
                        stat.rank = idx
                        stat.position = idx
            
            db.commit()
            logger.info(f"✅ Tabela de classificação construída para liga {league_id}")
                
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao construir tabela de classificação: {e}")
        finally:
            db.close()
    
    def export_league_data_to_json(self, league_id: int, output_file: str = None):
        """Exporta dados de uma liga para JSON no formato do example.json - PostgreSQL"""
        db = self.get_db_session()
        try:
            # Obtém informações da liga
            league = db.query(League).filter(League.id == league_id).first()
            
            if not league:
                logger.error(f"Liga {league_id} não encontrada no banco de dados")
                return None
            
            league_name = league.name
            country = league.country
            
            # Obtém tabela de classificação usando SQLAlchemy
            standings_query = db.query(
                TeamStatistics.rank,
                Team.id.label('team_id'),
                Team.name.label('team_name'),
                Team.image.label('team_logo'),
                TeamStatistics.points,
                (TeamStatistics.goals_for - TeamStatistics.goals_against).label('goals_diff'),
                TeamStatistics.matches_played,
                TeamStatistics.wins,
                TeamStatistics.draws,
                TeamStatistics.losses,
                TeamStatistics.goals_for,
                TeamStatistics.goals_against
            ).join(
                Team, TeamStatistics.team_id == Team.id
            ).filter(
                TeamStatistics.league_id == league_id
            ).order_by(
                TeamStatistics.rank
            ).all()
            
            # Formata os dados no padrão do example.json (versão simplificada)
            standings = []
            for row in standings_query:
                rank, team_id, team_name, team_logo, points, goals_diff, played, wins, draws, losses, goals_for, goals_against = (
                    row.rank, row.team_id, row.team_name, row.team_logo, row.points, 
                    row.goals_diff, row.matches_played, row.wins, row.draws, row.losses,
                    row.goals_for, row.goals_against
                )
                
                # Calcula aproveitamento geral
                aproveitamento = 0
                if played > 0:
                    max_points = played * 3
                    aproveitamento = round((points / max_points) * 100, 1)
                
                # Determina descrição baseada na posição
                if rank <= 4:
                    description = "Copa Libertadores"
                elif rank <= 6:
                    description = "Copa Sul-Americana"
                elif rank >= 17:
                    description = "Rebaixamento"
                else:
                    description = ""
                
                # Versão simplificada - dados básicos da tabela
                team_data = {
                    "rank": rank,
                    "team": {
                        "id": team_id,
                        "name": team_name,
                        "logo": team_logo or ""
                    },
                    "points": points,
                    "goalsDiff": goals_diff,
                    "group": f"{league_name} {league.season_year}",
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
                        "aproveitamento": aproveitamento,
                    },
                    "update": datetime.now().isoformat() + "+00:00",
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
            
            return export_data
                
        except Exception as e:
            logger.error(f"Erro ao exportar dados da liga {league_id}: {e}")
            return None
        finally:
            db.close()

