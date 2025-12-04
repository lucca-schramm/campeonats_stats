"""Endpoints de coleta de dados"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.core.database import get_db
from app.services.collection_service import CollectionService
from app.tasks.data_collection import collect_league_data_task
from app.models.league import League
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/trigger")
async def trigger_collection(
    league_id: Optional[int] = None,
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Dispara coleta de dados para uma liga ou todas.
    
    - Se `league_id` fornecido: coleta apenas essa liga
    - Se `force=True`: ignora verificação de necessidade e força coleta
    - Caso contrário: coleta apenas ligas com jogos próximos/ao vivo
    """
    try:
        # CollectionService precisa de sessão síncrona, então usamos SessionLocal
        from app.core.database import SessionLocal
        sync_db = SessionLocal()
        try:
            collection_service = CollectionService(sync_db)
            
            if league_id:
                # Verifica se liga existe
                result = await db.execute(
                    select(League).filter(League.id == league_id)
                )
                league = result.scalar_one_or_none()
                if not league:
                    raise HTTPException(status_code=404, detail="Liga não encontrada")
                
                # Verifica necessidade (a menos que force=True)
                if not force and not collection_service.should_collect_league(league_id):
                    return {
                        "message": "Liga não precisa de coleta no momento",
                        "league_id": league_id,
                        "skipped": True
                    }
                
                # Dispara coleta assíncrona
                from app.services.data_collector import LeagueConfig
                league_config = LeagueConfig(
                    id=league.id,
                    name=league.name,
                    country=league.country,
                    season_id=league.season_id,
                    season_year=league.season_year
                )
                
                collect_league_data_task.delay(league_config.__dict__)
                
                return {
                    "message": "Coleta iniciada",
                    "league_id": league_id,
                    "status": "queued"
                }
            
            # Coleta inteligente de múltiplas ligas
            priorities = collection_service.get_collection_priority()
            
            leagues_to_collect = []
            if force:
                # Força coleta de todas
                result = await db.execute(select(League))
                all_leagues = result.scalars().all()
                leagues_to_collect = [l.id for l in all_leagues]
            else:
                # Coleta apenas ligas prioritárias
                leagues_to_collect = priorities['high'] + priorities['medium']
            
            # Limita a 10 ligas por vez para respeitar API limits
            leagues_to_collect = leagues_to_collect[:10]
            
            for lid in leagues_to_collect:
                result = await db.execute(
                    select(League).filter(League.id == lid)
                )
                league = result.scalar_one_or_none()
                if league:
                    from app.services.data_collector import LeagueConfig
                    league_config = LeagueConfig(
                        id=league.id,
                        name=league.name,
                        country=league.country,
                        season_id=league.season_id,
                        season_year=league.season_year
                    )
                    collect_league_data_task.delay(league_config.__dict__)
            
            return {
                "message": f"Coleta iniciada para {len(leagues_to_collect)} ligas",
                "leagues_count": len(leagues_to_collect),
                "leagues": leagues_to_collect,
                "status": "queued"
            }
        finally:
            sync_db.close()
        
    except Exception as e:
        logger.error(f"Erro ao disparar coleta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initial")
async def trigger_initial_collection(db: AsyncSession = Depends(get_db)):
    """
    Força coleta inicial de dados (quando banco está vazio).
    Coleta todas as ligas disponíveis da API FootyStats.
    Executa de forma SÍNCRONA para garantir que funcione.
    """
    import traceback
    from io import StringIO
    
    log_buffer = StringIO()
    
    try:
        # Verifica se já há dados
        result = await db.execute(select(League))
        leagues = result.scalars().all()
        leagues_count = len(leagues)
        if leagues_count > 0:
            return {
                "message": f"Banco já possui {leagues_count} ligas",
                "status": "skipped",
                "leagues_count": leagues_count
            }
        
        # Executa coleta SÍNCRONA (sem Celery)
        logger.info("=" * 60)
        logger.info("INICIANDO COLETA INICIAL SÍNCRONA")
        logger.info("=" * 60)
        
        from app.services.data_collector import FootballDataCollector
        from app.core.config import settings
        
        if not settings.FOOTYSTATS_API_KEY:
            raise HTTPException(
                status_code=400, 
                detail="FOOTYSTATS_API_KEY não configurada no .env"
            )
        
        logger.info(f"API Key configurada: {settings.FOOTYSTATS_API_KEY[:20]}...")
        logger.info(f"API Base URL: {settings.API_BASE_URL}")
        
        try:
            collector = FootballDataCollector()
            logger.info("Collector criado. Iniciando coleta...")
            collector.collect_all_data()
            logger.info("Coleta executada com sucesso!")
        except ValueError as e:
            # Erro conhecido (ex: nenhuma liga encontrada)
            logger.error(f"Erro de validação: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Erro durante coleta: {e}")
            logger.error(f"Traceback: {error_trace}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro durante coleta: {str(e)}. Verifique logs para detalhes."
            )
        
        # Verifica resultado (usa nova sessão para garantir dados atualizados)
        from app.core.database import SessionLocal
        check_db = SessionLocal()
        try:
            new_count = check_db.query(League).count()
            logger.info(f"Verificação: {new_count} ligas encontradas no banco após coleta")
        finally:
            check_db.close()
        
        if new_count == 0:
            error_msg = "Coleta executada mas nenhuma liga foi salva. Verifique: 1) API key válida, 2) Ligas configuradas na API FootyStats, 3) Logs do container para erros."
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        logger.info("=" * 60)
        logger.info(f"COLETA CONCLUÍDA COM SUCESSO: {new_count} ligas")
        logger.info("=" * 60)
        
        return {
            "message": f"Coleta inicial concluída com sucesso",
            "status": "success",
            "leagues_collected": new_count,
            "note": f"{new_count} ligas foram coletadas e salvas no banco"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Erro ao executar coleta inicial: {e}")
        logger.error(f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Erro na coleta: {str(e)}")


@router.get("/status")
async def get_collection_status(db: AsyncSession = Depends(get_db)):
    """Retorna status das ligas e necessidade de coleta"""
    try:
        from app.core.database import SessionLocal
        sync_db = SessionLocal()
        try:
            from app.services.collection_service import CollectionService
            collection_service = CollectionService(sync_db)
            priorities = collection_service.get_collection_priority()
        finally:
            sync_db.close()
        
        result = await db.execute(select(League))
        leagues = result.scalars().all()
        
        result = {
            "total_leagues": len(leagues),
            "priorities": {
                "high": len(priorities['high']),
                "medium": len(priorities['medium']),
                "low": len(leagues) - len(priorities['high']) - len(priorities['medium'])
            },
            "recommended_collection": {
                "high": priorities['high'],
                "medium": priorities['medium']
            },
            "is_empty": len(leagues) == 0
        }
        
        return result
    except Exception as e:
        logger.error(f"Erro ao obter status de coleta: {e}")
        raise HTTPException(status_code=500, detail="Erro ao obter status de coleta")


@router.get("/debug")
async def debug_collection(db: AsyncSession = Depends(get_db)):
    """Endpoint de debug para verificar configuração"""
    from app.core.config import settings
    from app.core.database import SessionLocal
    from sqlalchemy import inspect, select
    
    try:
        # Verifica API key
        api_key_configured = bool(settings.FOOTYSTATS_API_KEY)
        api_key_preview = settings.FOOTYSTATS_API_KEY[:20] + "..." if api_key_configured else "NÃO CONFIGURADA"
        
        # Verifica banco
        result = await db.execute(select(League))
        leagues = result.scalars().all()
        leagues_count = len(leagues)
        
        # Verifica se tabelas existem (usa sync engine)
        from app.core.database import sync_engine
        inspector = inspect(sync_engine)
        tables = inspector.get_table_names()
        
        # Testa conexão com API
        api_test = None
        try:
            from app.services.data_collector import FootyStatsAPIClient
            if api_key_configured:
                client = FootyStatsAPIClient(settings.FOOTYSTATS_API_KEY)
                test_data = client.make_request("league-list", {"chosen_leagues_only": "true"})
                api_test = {
                    "status": "ok" if test_data else "erro",
                    "response_type": type(test_data).__name__,
                    "has_data": bool(test_data)
                }
        except Exception as e:
            api_test = {"status": "erro", "error": str(e)}
        
        return {
            "api_config": {
                "key_configured": api_key_configured,
                "key_preview": api_key_preview,
                "base_url": settings.API_BASE_URL,
                "test": api_test
            },
            "database": {
                "connected": True,
                "leagues_count": leagues_count,
                "tables": tables,
                "tables_count": len(tables)
            },
            "recommendation": "empty" if leagues_count == 0 else "ok"
        }
    except Exception as e:
        logger.error(f"Erro no debug: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

