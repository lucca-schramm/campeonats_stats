"""Endpoints para monitoramento de partidas ao vivo"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.live_match_service import LiveMatchService

router = APIRouter()


@router.get("/status")
async def get_live_matches_status(db: Session = Depends(get_db)):
    """Retorna status de partidas ao vivo e que precisam atualização"""
    service = LiveMatchService(db)
    summary = service.get_match_update_summary()
    return summary


@router.get("/")
async def get_live_matches(
    league_id: Optional[int] = Query(None, description="Filtrar por liga"),
    db: Session = Depends(get_db)
):
    """Retorna todas as partidas ao vivo"""
    service = LiveMatchService(db)
    matches = service.get_live_matches(league_id)
    
    return {
        "live_matches": [
            {
                "id": m.id,
                "league_id": m.league_id,
                "home_team": m.home_team_name,
                "away_team": m.away_team_name,
                "score": f"{m.home_goal_count}-{m.away_goal_count}",
                "status": m.status,
                "date_unix": m.date_unix
            }
            for m in matches
        ],
        "count": len(matches)
    }


@router.get("/upcoming")
async def get_upcoming_matches(
    minutes: int = Query(30, ge=1, le=120, description="Minutos à frente"),
    league_id: Optional[int] = Query(None, description="Filtrar por liga"),
    db: Session = Depends(get_db)
):
    """Retorna partidas que começam nas próximas X minutos"""
    service = LiveMatchService(db)
    matches = service.get_upcoming_matches(minutes, league_id)
    
    return {
        "upcoming_matches": [
            {
                "id": m.id,
                "league_id": m.league_id,
                "home_team": m.home_team_name,
                "away_team": m.away_team_name,
                "status": m.status,
                "date_unix": m.date_unix
            }
            for m in matches
        ],
        "count": len(matches),
        "minutes_ahead": minutes
    }

