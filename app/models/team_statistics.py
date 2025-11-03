"""Modelo TeamStatistics"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TeamStatistics(BaseModel):
    """Modelo de Estatísticas de Time"""
    __tablename__ = "team_statistics"
    
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False, index=True)
    season_id = Column(Integer, nullable=False, index=True)
    season_year = Column(Integer, nullable=False)
    
    matches_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    points = Column(Integer, default=0)
    rank = Column(Integer, default=0)
    position = Column(Integer, default=0)
    
    # Relationships
    team = relationship("Team", backref="statistics")
    league = relationship("League", backref="team_statistics")
    
    __table_args__ = (
        UniqueConstraint('team_id', 'league_id', 'season_id', name='uq_team_stats'),
    )
    
    def __repr__(self):
        return (
            f"<TeamStatistics(team_id={self.team_id}, league_id={self.league_id}, "
            f"points={self.points}, rank={self.rank})>"
        )

