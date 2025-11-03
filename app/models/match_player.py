"""Modelo MatchPlayer"""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class MatchPlayer(BaseModel):
    """Modelo de Jogador por Partida"""
    __tablename__ = "match_players"
    
    match_id = Column(Integer, ForeignKey("fixtures.id"), nullable=False, index=True)
    player_name = Column(String(255), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    position = Column(String(50), nullable=True)
    
    # Relationships
    fixture = relationship("Fixture", backref="match_players")
    team = relationship("Team", backref="match_players")
    
    __table_args__ = (
        UniqueConstraint('match_id', 'player_name', 'team_id', name='uq_match_player'),
    )
    
    def __repr__(self):
        return (
            f"<MatchPlayer(match_id={self.match_id}, player='{self.player_name}', "
            f"goals={self.goals})>"
        )

