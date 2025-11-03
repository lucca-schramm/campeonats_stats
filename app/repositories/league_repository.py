"""Repository de League"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.models.league import League


class LeagueRepository:
    """Repository para operações de banco com League"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[League]:
        """Obtém todas as ligas"""
        return self.db.query(League).offset(skip).limit(limit).all()
    
    def get_by_id(self, league_id: int) -> Optional[League]:
        """Obtém liga por ID"""
        return self.db.query(League).filter(League.id == league_id).first()
    
    def get_by_name(self, name: str) -> Optional[League]:
        """Obtém liga por nome (busca exata ou parcial)"""
        # Tenta busca exata primeiro
        league = self.db.query(League).filter(League.name.ilike(name)).first()
        if league:
            return league
        # Se não encontrar, tenta busca parcial
        return self.db.query(League).filter(League.name.ilike(f"%{name}%")).first()
    
    def search_by_name(self, query: str, limit: int = 10) -> List[League]:
        """Busca ligas por nome"""
        return self.db.query(League).filter(
            or_(
                League.name.ilike(f"%{query}%"),
                League.country.ilike(f"%{query}%")
            )
        ).limit(limit).all()
    
    def create(self, league_data: dict) -> League:
        """Cria nova liga"""
        league = League(**league_data)
        self.db.add(league)
        self.db.commit()
        self.db.refresh(league)
        return league
    
    def update(self, league: League, league_data: dict) -> League:
        """Atualiza liga"""
        for key, value in league_data.items():
            setattr(league, key, value)
        self.db.commit()
        self.db.refresh(league)
        return league
    
    def delete(self, league: League) -> bool:
        """Deleta liga"""
        self.db.delete(league)
        self.db.commit()
        return True

