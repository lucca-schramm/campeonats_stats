"""Service de Liga"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.league import League
from app.models.team_statistics import TeamStatistics
from app.models.player import Player
from app.repositories.league_repository import LeagueRepository


class LeagueService:
    """Service para operações com ligas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = LeagueRepository(db)
    
    def get_all_leagues(self, skip: int = 0, limit: int = 100) -> List[League]:
        """Obtém todas as ligas"""
        return self.repository.get_all(skip=skip, limit=limit)
    
    def get_league_by_id(self, league_id: int) -> Optional[League]:
        """Obtém liga por ID"""
        return self.repository.get_by_id(league_id)
    
    def get_league_by_name(self, name: str) -> Optional[League]:
        """Obtém liga por nome"""
        return self.repository.get_by_name(name)
    
    def search_leagues(self, query: str, limit: int = 10) -> List[League]:
        """Busca ligas por nome"""
        return self.repository.search_by_name(query, limit)
    
    def get_standings(self, league_id: int, season_id: Optional[int] = None) -> List[dict]:
        """Obtém tabela de classificação"""
        standings = self.db.query(TeamStatistics).filter(
            TeamStatistics.league_id == league_id
        )
        
        if season_id:
            standings = standings.filter(TeamStatistics.season_id == season_id)
        
        standings = standings.order_by(
            TeamStatistics.rank.asc(),
            TeamStatistics.points.desc()
        ).all()
        
        return [
            {
                "rank": s.rank,
                "team_id": s.team_id,
                "points": s.points,
                "matches_played": s.matches_played,
                "wins": s.wins,
                "draws": s.draws,
                "losses": s.losses,
                "goals_for": s.goals_for,
                "goals_against": s.goals_against,
                "goals_diff": s.goals_for - s.goals_against
            }
            for s in standings
        ]
    
    def get_top_scorers(self, league_id: int, limit: int = 20) -> List[dict]:
        """Obtém artilheiros da liga"""
        scorers = self.db.query(Player).filter(
            Player.league_id == league_id,
            Player.goals > 0
        ).order_by(
            Player.goals.desc(),
            Player.assists.desc()
        ).limit(limit).all()
        
        return [
            {
                "jogador-nome": p.name,
                "jogador-posicao": p.position or "N/A",
                "jogador-gols": p.goals,
                "jogador-assists": p.assists,
                "jogador-partidas": p.matches_played,
                "jogador-escudo": "",  # Será preenchido pelo repository se necessário
                "jogador-foto": p.url or ""
            }
            for p in scorers
        ]

