"""Modelo Player"""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Player(BaseModel):
    """Modelo de Jogador"""
    __tablename__ = "players"
    
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False, index=True)
    season_id = Column(Integer, nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    team_name = Column(String(255), nullable=True)
    position = Column(String(50), nullable=True)
    
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    matches_played = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    
    age = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    url = Column(String(500), nullable=True)
    
    clean_sheets = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    
    # Relationships
    team = relationship("Team", backref="players")
    league = relationship("League", backref="players")
    
    __table_args__ = (
        UniqueConstraint('name', 'team_id', 'season_id', name='uq_player_team_season'),
    )
    
    def __repr__(self):
        return f"<Player(name='{self.name}', goals={self.goals}, team_id={self.team_id})>"

