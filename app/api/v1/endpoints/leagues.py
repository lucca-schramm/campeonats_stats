"""Endpoints de Ligas"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.database import get_db
from app.core.cache import cache
from app.schemas.league import LeagueResponse
from app.services.league_service import LeagueService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def _get_cached_or_compute(
    cache_key: str,
    compute_func,
    ttl: int = 120,
    response_model=None
):
    """Helper para cache com fallback"""
    cached_result = await cache.get(cache_key)
    if cached_result:
        # Se veio do cache e temos response_model, converte dicts para models
        if response_model:
            if isinstance(cached_result, list):
                return [response_model(**item) if isinstance(item, dict) else item for item in cached_result]
            elif isinstance(cached_result, dict):
                return response_model(**cached_result)
        return cached_result
    
    result = await compute_func()
    
    # Serializa resultado para cache (converte Pydantic models para dict)
    if isinstance(result, list):
        serializable_result = [item.model_dump() if hasattr(item, 'model_dump') else item for item in result]
    elif hasattr(result, 'model_dump'):
        serializable_result = result.model_dump()
    else:
        serializable_result = result
    
    await cache.set(cache_key, serializable_result, ttl)
    return result


@router.get("/", response_model=List[LeagueResponse])
async def get_leagues(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas as ligas disponíveis"""
    cache_key = f"leagues:list:{skip}:{limit}"
    
    async def compute():
        service = LeagueService(db)
        leagues = await service.get_all_leagues(skip=skip, limit=limit)
        return [LeagueResponse.model_validate(league) for league in leagues]
    
    return await _get_cached_or_compute(cache_key, compute, response_model=LeagueResponse)


@router.get("/by-name", response_model=LeagueResponse)
async def get_league_by_name(
    name: str = Query(..., description="Nome da liga"),
    db: AsyncSession = Depends(get_db)
):
    """Obtém uma liga por nome"""
    cache_key = f"league:name:{name.lower()}"
    
    async def compute():
        service = LeagueService(db)
        league = await service.get_league_by_name(name)
        if not league:
            raise HTTPException(status_code=404, detail=f"Liga '{name}' não encontrada")
        return LeagueResponse.model_validate(league)
    
    return await _get_cached_or_compute(cache_key, compute, response_model=LeagueResponse)


@router.get("/{league_id}", response_model=LeagueResponse)
async def get_league(
    league_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtém uma liga por ID"""
    cache_key = f"league:{league_id}"
    
    async def compute():
        service = LeagueService(db)
        league = await service.get_league_by_id(league_id)
        if not league:
            raise HTTPException(status_code=404, detail="Liga não encontrada")
        return LeagueResponse.model_validate(league)
    
    return await _get_cached_or_compute(cache_key, compute, response_model=LeagueResponse)


@router.get("/{league_id}/standings")
@limiter.limit("200/minute")
async def get_league_standings(
    request: Request,
    league_id: int,
    season_id: Optional[int] = None,
    filter_type: Optional[str] = Query("geral", description="Tipo de filtro: geral, casa, fora"),
    db: AsyncSession = Depends(get_db)
):
    """Obtém tabela de classificação de uma liga"""
    if filter_type not in ["geral", "casa", "fora"]:
        filter_type = "geral"
    
    cache_key = f"league:{league_id}:standings:{season_id}:{filter_type}"
    
    async def compute():
        service = LeagueService(db)
        standings = await service.get_standings(league_id, season_id, filter_type)
        return {"league_id": league_id, "standings": standings}
    
    return await _get_cached_or_compute(cache_key, compute)


@router.get("/{league_id}/top-scorers")
async def get_top_scorers(
    league_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Obtém artilharia da liga"""
    cache_key = f"league:{league_id}:top_scorers:{limit}"
    
    async def compute():
        service = LeagueService(db)
        scorers = await service.get_top_scorers(league_id, limit)
        return {"league_id": league_id, "top_scorers": scorers}
    
    return await _get_cached_or_compute(cache_key, compute)

