"""Tasks de coleta de dados"""
from app.tasks.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def collect_league_data_task(self, league_config_dict: dict):
    """Tarefa assíncrona para coletar dados de uma liga"""
    try:
        from app.services.data_collector import FootballDataCollector, LeagueConfig
        
        league_config = LeagueConfig(**league_config_dict)
        collector = FootballDataCollector()
        collector.collect_league_data(league_config)
        
        return {"status": "success", "league_id": league_config.id}
    except Exception as e:
        logger.error(f"Erro ao coletar dados da liga: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))



