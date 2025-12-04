"""Tasks para monitoramento e atualização de partidas ao vivo em tempo real"""
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.live_match_service import LiveMatchService
from app.models.fixture import Fixture
from app.models.league import League
from app.services.data_collector import FootyStatsAPIClient
from app.core.config import settings
import logging
import time

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def update_live_matches_task(self):
    """
    Task leve para atualizar apenas partidas ao vivo.
    Roda frequentemente (a cada 1-2 minutos) para manter dados atualizados em tempo real.
    """
    db = SessionLocal()
    try:
        live_service = LiveMatchService(db)
        summary = live_service.get_match_update_summary()
        
        if summary["total_to_update"] == 0:
            logger.debug("Nenhuma partida precisa atualização no momento")
            return {"status": "skipped", "reason": "no_matches_to_update"}
        
        logger.info(
            f"Atualizando partidas: {summary['live_matches']} ao vivo, "
            f"{summary['upcoming_matches']} próximas, {summary['recently_finished']} finalizadas"
        )
        
        # Busca partidas que precisam atualização
        matches_to_update = live_service.get_matches_to_update()
        
        if not matches_to_update:
            return {"status": "skipped", "reason": "no_matches_found"}
        
        # Agrupa por liga para otimizar chamadas à API
        matches_by_league = {}
        for match in matches_to_update:
            if match.league_id not in matches_by_league:
                matches_by_league[match.league_id] = []
            matches_by_league[match.league_id].append(match)
        
        # Inicializa API client
        api = FootyStatsAPIClient(settings.FOOTYSTATS_API_KEY)
        
        updated_count = 0
        error_count = 0
        
        # Atualiza partidas por liga
        for league_id, matches in matches_by_league.items():
            try:
                # Busca liga para obter season_id
                league = db.query(League).filter(League.id == league_id).first()
                if not league:
                    logger.warning(f"Liga {league_id} não encontrada")
                    continue
                
                # Busca todas as partidas da liga da API (mais eficiente que buscar uma por uma)
                fixtures_data = api.get_league_matches(league.season_id)
                
                # Cria mapa de partidas por ID
                fixtures_map = {f.get("id"): f for f in fixtures_data if f.get("id")}
                
                # Atualiza cada partida
                for match in matches:
                    fixture_data = fixtures_map.get(match.id)
                    if fixture_data:
                        _update_fixture_from_api_data(db, match, fixture_data)
                        updated_count += 1
                    else:
                        logger.warning(f"Partida {match.id} não encontrada na API")
                        error_count += 1
                
                # Pequeno delay para não sobrecarregar API
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Erro ao atualizar partidas da liga {league_id}: {e}")
                error_count += len(matches)
        
        # Atualiza tabela de classificação das ligas com partidas ao vivo
        leagues_to_update = live_service.get_leagues_with_live_matches()
        for league_id in leagues_to_update:
            try:
                league = db.query(League).filter(League.id == league_id).first()
                if league:
                    from app.services.data_collector import FootballDataCollector
                    collector = FootballDataCollector()
                    collector.build_league_table_from_matches(
                        league_id, league.season_id, league.season_year
                    )
            except Exception as e:
                logger.error(f"Erro ao atualizar tabela da liga {league_id}: {e}")
        
        db.commit()
        
        logger.info(f"Atualizadas {updated_count} partidas ({error_count} erros)")
        
        return {
            "status": "success",
            "updated": updated_count,
            "errors": error_count,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Erro crítico ao atualizar partidas ao vivo: {e}")
        db.rollback()
        # Retry com backoff exponencial
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
    finally:
        db.close()


def _update_fixture_from_api_data(db, fixture: Fixture, api_data: dict):
    """Atualiza uma partida com dados da API"""
    try:
        # Atualiza status
        new_status = api_data.get("status", fixture.status)
        if new_status != fixture.status:
            fixture.status = new_status
        
        # Atualiza placar
        home_goals = api_data.get("homeGoalCount", 0)
        away_goals = api_data.get("awayGoalCount", 0)
        
        if home_goals != fixture.home_goal_count or away_goals != fixture.away_goal_count:
            fixture.home_goal_count = home_goals
            fixture.away_goal_count = away_goals
            fixture.total_goal_count = home_goals + away_goals
        
        # Atualiza estatísticas se disponíveis
        if "home_corners" in api_data:
            fixture.home_corners = api_data.get("home_corners", 0)
            fixture.away_corners = api_data.get("away_corners", 0)
        
        if "home_possession" in api_data:
            fixture.home_possession = api_data.get("home_possession", 0)
            fixture.away_possession = api_data.get("away_possession", 0)
        
        if "home_shots" in api_data:
            fixture.home_shots = api_data.get("home_shots", 0)
            fixture.away_shots = api_data.get("away_shots", 0)
        
        # Atualiza data se mudou
        if "date_unix" in api_data and api_data["date_unix"]:
            fixture.date_unix = api_data["date_unix"]
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Erro ao atualizar partida {fixture.id}: {e}")
        db.rollback()
        raise

