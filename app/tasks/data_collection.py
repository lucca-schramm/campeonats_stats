"""Tasks de coleta de dados"""
from app.tasks.celery_app import celery_app
from app.webhooks.manager import WebhookManager
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def collect_league_data_task(self, league_config_dict: dict):
    """
    Tarefa assíncrona para coletar dados de uma liga.
    
    Mantém compatibilidade com código original do main.py
    """
    try:
        # Importa aqui para evitar circular imports
        from main import FootballDataCollector, LeagueConfig
        from dataclasses import asdict
        
        league_config = LeagueConfig(**league_config_dict)
        collector = FootballDataCollector()
        collector.collect_league_data(league_config)
        
        # Dispara webhook após coleta
        webhook_manager = WebhookManager()
        webhook_manager.trigger_webhook(
            event_type="standings_updated",
            league_id=league_config.id,
            data={"league_name": league_config.name, "status": "updated"}
        )
        
        return {"status": "success", "league_id": league_config.id}
    except Exception as e:
        logger.error(f"Erro ao coletar dados da liga: {e}")
        # Retry com backoff exponencial
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def export_league_json_task(league_id: int):
    """Tarefa assíncrona para exportar JSON"""
    try:
        from main import FootballDataCollector
        
        collector = FootballDataCollector()
        result = collector.export_league_data_to_json(league_id)
        
        # Dispara webhook
        webhook_manager = WebhookManager()
        webhook_manager.trigger_webhook(
            event_type="standings_updated",
            league_id=league_id,
            data={"status": "exported"}
        )
        
        return {"status": "success", "league_id": league_id}
    except Exception as e:
        logger.error(f"Erro ao exportar JSON: {e}")
        raise


@celery_app.task
def trigger_webhook_task(event_type: str, league_id: int, data: dict):
    """Tarefa assíncrona para disparar webhook"""
    try:
        webhook_manager = WebhookManager()
        webhook_manager.trigger_webhook(event_type, league_id, data)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Erro ao disparar webhook: {e}")
        raise

