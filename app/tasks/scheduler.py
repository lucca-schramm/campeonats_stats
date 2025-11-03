"""Agendamento inteligente de coleta"""
from celery.schedules import crontab
from datetime import datetime
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.collection_service import CollectionService
from app.models.league import League
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def scheduled_collection():
    """Coleta periódica inteligente - roda a cada 15 minutos"""
    db = SessionLocal()
    try:
        service = CollectionService(db)
        priorities = service.get_collection_priority()
        
        # Coleta apenas ligas prioritárias (limite de 10 para respeitar API)
        leagues_to_collect = (priorities['high'] + priorities['medium'])[:10]
        
        if not leagues_to_collect:
            logger.info("Nenhuma liga precisa de coleta no momento")
            return {"status": "skipped", "reason": "no_leagues_need_update"}
        
        # Importa aqui para evitar circular import
        from app.tasks.data_collection import collect_league_data_task
        from main import LeagueConfig
        
        for league_id in leagues_to_collect:
            league = db.query(League).filter(League.id == league_id).first()
            if league:
                league_config = LeagueConfig(
                    id=league.id,
                    name=league.name,
                    country=league.country,
                    season_id=league.season_id,
                    season_year=league.season_year
                )
                collect_league_data_task.delay(league_config.__dict__)
        
        logger.info(f"Coleta agendada para {len(leagues_to_collect)} ligas")
        return {
            "status": "queued",
            "leagues_count": len(leagues_to_collect),
            "leagues": leagues_to_collect
        }
        
    except Exception as e:
        logger.error(f"Erro no agendamento de coleta: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

