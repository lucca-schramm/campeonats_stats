"""Endpoints de Ligas"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.database import get_db
from app.core.cache import cache
from app.schemas.league import LeagueResponse
from app.services.league_service import LeagueService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=List[LeagueResponse])
async def get_leagues(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Lista todas as ligas disponíveis"""
    cache_key = f"leagues:list:{skip}:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    service = LeagueService(db)
    leagues = service.get_all_leagues(skip=skip, limit=limit)
    
    result = [LeagueResponse.model_validate(league) for league in leagues]
    cache.set(cache_key, result, ttl=120)
    return result


@router.get("/by-name", response_model=LeagueResponse)
async def get_league_by_name(
    name: str = Query(..., description="Nome da liga"),
    db: Session = Depends(get_db)
):
    """Obtém uma liga por nome"""
    cache_key = f"league:name:{name.lower()}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    service = LeagueService(db)
    league = service.get_league_by_name(name)
    
    if not league:
        raise HTTPException(status_code=404, detail=f"Liga '{name}' não encontrada")
    
    result = LeagueResponse.model_validate(league)
    cache.set(cache_key, result, ttl=120)
    return result


@router.get("/{league_id}", response_model=LeagueResponse)
async def get_league(
    league_id: int,
    db: Session = Depends(get_db)
):
    """Obtém uma liga por ID"""
    cache_key = f"league:{league_id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    service = LeagueService(db)
    league = service.get_league_by_id(league_id)
    
    if not league:
        raise HTTPException(status_code=404, detail="Liga não encontrada")
    
    result = LeagueResponse.model_validate(league)
    cache.set(cache_key, result, ttl=120)
    return result


@router.get("/{league_id}/standings")
@limiter.limit("200/minute")  # Rate limit específico
async def get_league_standings(
    request: Request,
    league_id: int,
    season_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Obtém tabela de classificação de uma liga"""
    cache_key = f"league:{league_id}:standings:{season_id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    service = LeagueService(db)
    standings = service.get_standings(league_id, season_id)
    
    cache.set(cache_key, standings, ttl=120)
    return {"league_id": league_id, "standings": standings}


@router.get("/{league_id}/top-scorers")
async def get_top_scorers(
    league_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtém artilharia da liga"""
    cache_key = f"league:{league_id}:top_scorers:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    service = LeagueService(db)
    scorers = service.get_top_scorers(league_id, limit)
    
    cache.set(cache_key, scorers, ttl=120)
    return {"league_id": league_id, "top_scorers": scorers}

