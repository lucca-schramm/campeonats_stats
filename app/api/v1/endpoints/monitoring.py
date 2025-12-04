"""Endpoints de monitoramento do sistema"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.league import League
from app.models.team import Team
from app.models.fixture import Fixture
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """
    Retorna status completo do sistema:
    - Status do banco de dados
    - Estatísticas de coleta
    - Rate limiting
    - Última coleta
    """
    try:
        # Conta dados no banco
        result = await db.execute(select(func.count(League.id)))
        leagues_count = result.scalar() or 0
        
        result = await db.execute(select(func.count(Team.id)))
        teams_count = result.scalar() or 0
        
        result = await db.execute(select(func.count(Fixture.id)))
        fixtures_count = result.scalar() or 0
        
        # Status do rate limiter
        rate_limiter_stats = {}
        try:
            from app.services.api_rate_limiter import get_rate_limiter
            rate_limiter = get_rate_limiter()
            rate_limiter_stats = rate_limiter.get_stats()
        except Exception as e:
            logger.warning(f"Erro ao obter stats do rate limiter: {e}")
        
        # Status do banco
        database_status = "populated" if leagues_count > 0 else "empty"
        
        return {
            "status": "ok",
            "database": {
                "status": database_status,
                "leagues": leagues_count,
                "teams": teams_count,
                "fixtures": fixtures_count
            },
            "rate_limiter": rate_limiter_stats,
            "collection": {
                "needs_initial_collection": leagues_count == 0,
                "auto_collection_enabled": True
            }
        }
    except Exception as e:
        logger.error(f"Erro ao obter status do sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

