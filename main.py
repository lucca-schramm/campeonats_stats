import os
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import IntegrityError

# Imports do banco de dados PostgreSQL
from app.core.database import SessionLocal
from app.models.league import League
from app.models.team import Team
from app.models.fixture import Fixture
from app.models.player import Player
from app.models.team_statistics import TeamStatistics

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configurações da API FootyStats
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("FOOTYSTATS_API_KEY")

if not API_KEY:
    raise ValueError("FOOTYSTATS_API_KEY não configurada no arquivo .env")


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
    """Coletor principal de dados de futebol - PostgreSQL"""
    
    def __init__(self):
        self.api = FootyStatsAPIClient(API_KEY)
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
        
        # Ordena por ano (mais recente primeiro)
        sorted_seasons = sorted(seasons, key=lambda x: x.get("year", 0), reverse=True)
        return sorted_seasons[0]
    
    def get_league_id_from_database(self, season_id: int, league_name: str, country: str) -> int:
        """Busca o league_id correto no banco de dados baseado no season_id"""
        db = self.get_db_session()
        try:
            # Busca o league_id que tem mais fixtures para este season_id
            result = db.query(Fixture.league_id, func.count(Fixture.id).label('fixture_count')).filter(
                Fixture.season_id == season_id
            ).group_by(Fixture.league_id).order_by(func.count(Fixture.id).desc()).first()
            
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
        finally:
            db.close()
    
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
        db = self.get_db_session()
        try:
            fixture = db.query(Fixture).filter(Fixture.id == fixture_id).first()
            
            if not fixture:
                return True  # Partida não existe, deve ser criada
            
            new_status = fixture_data.get("status", "")
            new_home_goals = fixture_data.get("homeGoalCount", 0)
            new_away_goals = fixture_data.get("awayGoalCount", 0)
            
            # Sempre atualiza se:
            # 1. Status mudou (ex: de "scheduled" para "complete")
            # 2. Placar mudou
            # 3. Partida foi criada há mais de 24h e ainda não está completa
            if (fixture.status != new_status or 
                fixture.home_goal_count != new_home_goals or 
                fixture.away_goal_count != new_away_goals):
                return True
            
            # Se a partida não está completa e foi criada há mais de 24h, atualiza
            if (new_status not in ["complete", "finished"] and 
                fixture.created_at and 
                (datetime.now() - fixture.created_at).total_seconds() > 86400):
                return True
            
            return False
        finally:
            db.close()
    
    
    
    
    
    
    def save_league(self, league_data: Dict) -> int:
        """Salva uma liga no banco de dados PostgreSQL"""
        db = self.get_db_session()
        try:
            league = db.query(League).filter(League.id == league_data["id"]).first()
            
            if league:
                # Atualiza registro existente
                league.name = league_data["name"]
                league.country = league_data["country"]
                league.image = league_data.get("image")
                league.season_id = league_data["season_id"]
                league.season_year = league_data["season_year"]
            else:
                # Cria novo registro
                league = League(
                    id=league_data["id"],
                    name=league_data["name"],
                    country=league_data["country"],
                    image=league_data.get("image"),
                    season_id=league_data["season_id"],
                    season_year=league_data["season_year"]
                )
                db.add(league)
            
            db.commit()
            return league_data["id"]
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar liga: {e}")
            raise
        finally:
            db.close()
    
    def save_team(self, team_data: Dict, league_id: int, season_id: int) -> int:
        """Salva um time no banco de dados PostgreSQL"""
        db = self.get_db_session()
        try:
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
            team = db.query(Team).filter(
                Team.id == team_id,
                Team.league_id == league_id,
                Team.season_id == season_id
            ).first()
            
            if team:
                # Atualiza registro existente
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
                # Insere novo registro
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
                    season_id=season_id
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
            
            # Busca partida existente
            fixture = db.query(Fixture).filter(Fixture.id == fixture_id).first()
            
            if fixture:
                # Atualiza registro existente
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
                logger.debug(f"Partida atualizada: ID {fixture_id} - {home_team_name} vs {away_team_name}")
            else:
                # Insere novo registro
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
                    stadium_name=fixture_data.get("stadium_name")
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
            # Adapta os dados da FootyStats para o formato interno
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
                # Atualiza registro existente
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
                # Cria novo registro
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
                    position=team_stats.get("position", 0)
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
            # Obtém nome do time
            team = db.query(Team).filter(Team.id == team_id).first()
            team_name = team.name if team else "Unknown"
            
            # Validação de dados do jogador
            player_name = player_data.get("name", "").strip()
            if not player_name or player_name == "N/A" or player_name == "Unknown":
                logger.debug(f"⏭️  Jogador sem nome válido pulado para team_id {team_id}: '{player_name}'")
                return None
            
            # Verifica se já existe um jogador com este nome para este time e temporada
            player = db.query(Player).filter(
                Player.name == player_name,
                Player.team_id == team_id,
                Player.season_id == season_id
            ).first()
            
            if player:
                # Atualiza registro existente
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
                # Insere novo registro
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
                    red_cards=player_data.get("red_cards", 0) or 0
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
    
    def save_match_player(self, match_id: int, player_data: Dict, team_id: int) -> int:
        """Salva dados de um jogador em uma partida específica - PostgreSQL"""
        # Nota: Este método pode não ser necessário se não houver modelo MatchPlayer
        # Mantido para compatibilidade, mas pode ser removido se não usado
        logger.warning("save_match_player chamado mas modelo MatchPlayer pode não existir")
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
        """Obtém artilharia do banco de dados PostgreSQL"""
        db = self.get_db_session()
        try:
            # Query usando SQLAlchemy
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
        finally:
            db.close()

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
            
            # Processa a liga
            thread_collector.collect_league_data(league_config)
            return True
        except Exception as e:
            logger.error(f"❌ Erro na thread para liga {league_config.name}: {e}")
            return False
    
    def build_league_table_from_matches(self, league_id: int, season_id: int, season_year: int = None):
        """Constrói tabela de classificação a partir dos dados de partidas coletados - PostgreSQL"""
        db = self.get_db_session()
        try:
            # Obtém todos os times da liga usando season_id como identificador único
            teams = db.query(Team.id, Team.name).filter(Team.season_id == season_id).all()
            
            if not teams:
                logger.warning(f"Nenhum time encontrado para liga {league_id}")
                return
            
            # Para cada time, calcula estatísticas
            for team_id, team_name in teams:
                # Partidas como mandante (apenas completas)
                home_query = db.query(
                    func.count(Fixture.id).label('matches'),
                    func.sum(func.case((Fixture.home_goal_count > Fixture.away_goal_count, 1), else_=0)).label('wins'),
                    func.sum(func.case((Fixture.home_goal_count == Fixture.away_goal_count, 1), else_=0)).label('draws'),
                    func.sum(func.case((Fixture.home_goal_count < Fixture.away_goal_count, 1), else_=0)).label('losses'),
                    func.sum(Fixture.home_goal_count).label('goals_for'),
                    func.sum(Fixture.away_goal_count).label('goals_against')
                ).filter(
                    Fixture.season_id == season_id,
                    Fixture.home_team_id == team_id,
                    Fixture.status == 'complete'
                ).first()
                
                home_stats = (home_query.matches or 0, home_query.wins or 0, home_query.draws or 0,
                             home_query.losses or 0, home_query.goals_for or 0, home_query.goals_against or 0)
                
                # Partidas como visitante (apenas completas)
                away_query = db.query(
                    func.count(Fixture.id).label('matches'),
                    func.sum(func.case((Fixture.away_goal_count > Fixture.home_goal_count, 1), else_=0)).label('wins'),
                    func.sum(func.case((Fixture.away_goal_count == Fixture.home_goal_count, 1), else_=0)).label('draws'),
                    func.sum(func.case((Fixture.away_goal_count < Fixture.home_goal_count, 1), else_=0)).label('losses'),
                    func.sum(Fixture.away_goal_count).label('goals_for'),
                    func.sum(Fixture.home_goal_count).label('goals_against')
                ).filter(
                    Fixture.season_id == season_id,
                    Fixture.away_team_id == team_id,
                    Fixture.status == 'complete'
                ).first()
                
                away_stats = (away_query.matches or 0, away_query.wins or 0, away_query.draws or 0,
                             away_query.losses or 0, away_query.goals_for or 0, away_query.goals_against or 0)
                
                # Calcula totais
                total_matches = home_stats[0] + away_stats[0]
                total_wins = home_stats[1] + away_stats[1]
                total_draws = home_stats[2] + away_stats[2]
                total_losses = home_stats[3] + away_stats[3]
                total_goals_for = home_stats[4] + away_stats[4]
                total_goals_against = home_stats[5] + away_stats[5]
                total_points = (total_wins * 3) + (total_draws * 1)
                
                # Verifica se já existe estatística para este time/liga/temporada
                stats = db.query(TeamStatistics).filter(
                    TeamStatistics.team_id == team_id,
                    TeamStatistics.league_id == league_id,
                    TeamStatistics.season_id == season_id
                ).first()
                
                if stats:
                    # Atualiza registro existente
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
                    # Insere novo registro
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
                        position=0
                    )
                    db.add(stats)
                
                # Atualiza posições na tabela seguindo critérios de desempate:
                # 1) Maior número de vitórias; 2) Maior saldo de gols; 3) Maior número de gols pró;
                # 4) Confronto direto (entre clubes empatados nos critérios anteriores);
                # 5) Menor número de cartões vermelhos; 6) Menor número de cartões amarelos.
                # Implementação: calculamos as chaves de desempate em Python e persistimos rank/position.

            # Carrega estatísticas atuais dos times nesta temporada
            stats_list = db.query(TeamStatistics).filter(
                TeamStatistics.league_id == league_id,
                TeamStatistics.season_id == season_id
            ).all()

            # Mapa base por time
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

                # Cartões por time (soma home/away) - usando SQLAlchemy
                for team_id in team_ids:
                    # Red cards
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

                # Agrupa times empatados antes de confronto direto: pontos, vitórias, gd, gf
                from collections import defaultdict
                groups = defaultdict(list)
                for t in team_rows.values():
                    groups[(t["points"], t["wins"], t["gd"], t["gf"])].append(t["team_id"])

                # Calcula pontos de confronto direto por grupo com mais de 1 time
                for key, tied_team_ids in groups.items():
                    if len(tied_team_ids) <= 1:
                        continue
                    
                    # Para cada time do grupo, calcula pontos contra os demais do mesmo grupo
                    for team_id in tied_team_ids:
                        h2h_points = 0
                        # Partidas como mandante
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
                        
                        # Partidas como visitante
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
