"""Agendamento de coleta"""
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.league import League
import logging

logger = logging.getLogger(__name__)


@celery_app.task
def check_and_collect_if_empty():
    """Verifica se banco está vazio e dispara coleta"""
    db = SessionLocal()
    try:
        leagues_count = db.query(League).count()
        if leagues_count > 0:
            logger.debug(f"Banco já possui {leagues_count} ligas. Coleta não necessária.")
            return {"status": "skipped", "reason": "database_populated", "leagues": leagues_count}
        
        logger.info("⚠️ Banco vazio detectado. Disparando coleta inicial...")
        # Chama diretamente a task ao invés de usar send_task para evitar problemas de registro
        from app.tasks.scheduler import initial_data_collection
        result = initial_data_collection.delay()
        logger.info(f"✅ Task de coleta disparada (ID: {result.id})")
        return {"status": "queued", "task_id": result.id}
    except Exception as e:
        logger.error(f"❌ Erro ao verificar banco vazio: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        db.close()




@celery_app.task
def periodic_full_collection():
    """Coleta periódica otimizada - atualiza ligas em rodízio"""
    db = SessionLocal()
    try:
        from sqlalchemy import func, or_
        from datetime import datetime, timedelta
        
        # Busca todas as ligas ordenadas por updated_at (mais antigas primeiro)
        leagues = db.query(League).order_by(League.updated_at.asc()).all()
        
        if not leagues:
            logger.info("Nenhuma liga no banco. Coleta periódica ignorada.")
            return {"status": "skipped", "reason": "no_leagues_in_database"}
        
        # Otimização: processa em lotes de 2 ligas por vez para não sobrecarregar API
        # Prioriza ligas que não foram atualizadas há mais tempo
        batch_size = 2
        total_leagues = len(leagues)
        leagues_to_collect = leagues[:batch_size]
        
        # Calcula há quanto tempo cada liga foi atualizada
        now = datetime.utcnow()
        leagues_info = []
        for league in leagues_to_collect:
            last_update = league.updated_at if league.updated_at else league.created_at
            hours_since_update = (now - last_update).total_seconds() / 3600 if last_update else 999
            leagues_info.append({
                "id": league.id,
                "name": league.name,
                "hours_since_update": round(hours_since_update, 1)
            })
        
        # Formata informações das ligas
        leagues_str = ', '.join([
            f"{l['name']} ({l['hours_since_update']}h)" 
            for l in leagues_info
        ])
        logger.info(
            f"🔄 Coleta periódica: atualizando {len(leagues_to_collect)} de {total_leagues} ligas "
            f"(lote rotativo - {leagues_str})"
        )
        
        from app.tasks.data_collection import collect_league_data_task
        from app.services.data_collector import LeagueConfig
        
        task_ids = []
        for league in leagues_to_collect:
            league_config = LeagueConfig(
                id=league.id,
                name=league.name,
                country=league.country,
                season_id=league.season_id,
                season_year=league.season_year
            )
            result = collect_league_data_task.delay(league_config.__dict__)
            task_ids.append(result.id)
            logger.debug(f"Task enfileirada para liga {league.name} (ID: {result.id})")
        
        logger.info(f"✅ {len(task_ids)} tasks de coleta enfileiradas")
        return {
            "status": "queued",
            "leagues_count": len(leagues_to_collect),
            "total_leagues": total_leagues,
            "task_ids": task_ids,
            "leagues_info": leagues_info
        }
    except Exception as e:
        logger.error(f"❌ Erro na coleta periódica: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def initial_data_collection(self):
    """Coleta inicial de dados via Celery - coleta TODAS as ligas completamente"""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        from app.models.team import Team
        
        # Verifica se já temos dados completos (ligas com times)
        leagues_with_teams = db.query(func.count(func.distinct(Team.league_id))).scalar() or 0
        total_leagues = db.query(League).count()
        
        if leagues_with_teams == total_leagues and total_leagues > 0:
            logger.info(f"✅ Banco já possui dados completos: {total_leagues} ligas com times coletados")
            return {
                "status": "skipped", 
                "reason": "database_already_populated", 
                "leagues": total_leagues,
                "leagues_with_data": leagues_with_teams
            }
        
        logger.info("🚀 Iniciando coleta inicial COMPLETA de dados")
        from app.services.data_collector import FootballDataCollector
        from app.core.config import settings
        
        if not settings.FOOTYSTATS_API_KEY:
            error_msg = "FOOTYSTATS_API_KEY não configurada"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}
        
        collector = FootballDataCollector()
        
        # Se já temos ligas mas sem dados completos, coleta apenas as que faltam
        if total_leagues > 0 and leagues_with_teams < total_leagues:
            logger.info(f"📊 Coletando dados faltantes: {total_leagues - leagues_with_teams} ligas sem dados completos")
            # Carrega ligas da API
            collector.load_leagues_from_api()
            
            # Coleta dados de cada liga que não tem times
            for league_config in collector.leagues:
                league = db.query(League).filter(League.id == league_config.id).first()
                if league:
                    # Verifica se já tem times
                    teams_count = db.query(Team).filter(Team.league_id == league.id).count()
                    if teams_count == 0:
                        logger.info(f"📥 Coletando dados completos da liga: {league.name}")
                        try:
                            collector.collect_league_data(league_config)
                            logger.info(f"✅ Liga {league.name} coletada com sucesso")
                        except Exception as e:
                            logger.error(f"❌ Erro ao coletar liga {league.name}: {e}", exc_info=True)
        else:
            # Coleta inicial completa
            collector.collect_all_data()
        
        db.close()
        db = SessionLocal()
        
        # Verifica resultado
        final_leagues = db.query(League).count()
        final_teams = db.query(Team).count()
        final_leagues_with_data = db.query(func.count(func.distinct(Team.league_id))).scalar() or 0
        
        if final_leagues_with_data == 0:
            error_msg = "Coleta executada mas nenhuma liga tem dados completos"
            logger.error(error_msg)
            if self.request.retries < self.max_retries:
                raise self.retry(exc=Exception(error_msg), countdown=180)
            return {"status": "error", "error": error_msg}
        
        logger.info(f"✅ Coleta inicial concluída: {final_leagues} ligas, {final_teams} times, {final_leagues_with_data} ligas com dados completos")
        return {
            "status": "success", 
            "leagues_collected": final_leagues,
            "teams_collected": final_teams,
            "leagues_with_complete_data": final_leagues_with_data
        }
        
    except Exception as e:
        if self.request.retries >= self.max_retries:
            logger.error(f"❌ Erro na coleta após {self.max_retries} tentativas: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
        
        wait_time = 120 * (2 ** self.request.retries)
        logger.info(f"🔄 Retry em {wait_time}s...")
        raise self.retry(exc=e, countdown=wait_time)
    finally:
        db.close()