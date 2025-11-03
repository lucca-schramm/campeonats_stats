"""Endpoints de coleta de dados"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
    db: Session = Depends(get_db)
):
    """
    Dispara coleta de dados para uma liga ou todas.
    
    - Se `league_id` fornecido: coleta apenas essa liga
    - Se `force=True`: ignora verificação de necessidade e força coleta
    - Caso contrário: coleta apenas ligas com jogos próximos/ao vivo
    """
    try:
        collection_service = CollectionService(db)
        
        if league_id:
            # Verifica se liga existe
            league = db.query(League).filter(League.id == league_id).first()
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
            from main import LeagueConfig
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
            all_leagues = db.query(League).all()
            leagues_to_collect = [l.id for l in all_leagues]
        else:
            # Coleta apenas ligas prioritárias
            leagues_to_collect = priorities['high'] + priorities['medium']
        
        # Limita a 10 ligas por vez para respeitar API limits
        leagues_to_collect = leagues_to_collect[:10]
        
        for lid in leagues_to_collect:
            league = db.query(League).filter(League.id == lid).first()
            if league:
                from main import LeagueConfig
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
        
    except Exception as e:
        logger.error(f"Erro ao disparar coleta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_collection_status(db: Session = Depends(get_db)):
    """Retorna status das ligas e necessidade de coleta"""
    try:
        collection_service = CollectionService(db)
        priorities = collection_service.get_collection_priority()
        
        leagues = db.query(League).all()
        
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
            }
        }
        
        return result
    except Exception as e:
        logger.error(f"Erro ao obter status de coleta: {e}")
        raise HTTPException(status_code=500, detail="Erro ao obter status de coleta")

