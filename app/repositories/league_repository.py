"""Repository de League (Async)"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, delete
from typing import List, Optional
from app.models.league import League


class LeagueRepository:
    """Repository async para operações de banco com League"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[League]:
        """Obtém todas as ligas"""
        result = await self.db.execute(
            select(League).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_id(self, league_id: int) -> Optional[League]:
        """Obtém liga por ID"""
        result = await self.db.execute(
            select(League).filter(League.id == league_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[League]:
        """Obtém liga por nome (busca exata ou parcial)"""
        # Tenta busca exata primeiro
        result = await self.db.execute(
            select(League).filter(League.name.ilike(name))
        )
        league = result.scalar_one_or_none()
        if league:
            return league
        # Se não encontrar, tenta busca parcial
        result = await self.db.execute(
            select(League).filter(League.name.ilike(f"%{name}%"))
        )
        return result.scalar_one_or_none()
    
    async def search_by_name(self, query: str, limit: int = 10) -> List[League]:
        """Busca ligas por nome"""
        result = await self.db.execute(
            select(League).filter(
                or_(
                    League.name.ilike(f"%{query}%"),
                    League.country.ilike(f"%{query}%")
                )
            ).limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, league_data: dict) -> League:
        """Cria nova liga"""
        league = League(**league_data)
        self.db.add(league)
        await self.db.commit()
        await self.db.refresh(league)
        return league
    
    async def update(self, league: League, league_data: dict) -> League:
        """Atualiza liga"""
        for key, value in league_data.items():
            setattr(league, key, value)
        await self.db.commit()
        await self.db.refresh(league)
        return league
    
    async def delete(self, league: League) -> bool:
        """Deleta liga"""
        await self.db.execute(delete(League).where(League.id == league.id))
        await self.db.commit()
        return True

