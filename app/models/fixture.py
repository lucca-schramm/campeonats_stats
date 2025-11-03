"""Modelo Fixture"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Float, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Fixture(BaseModel):
    """Modelo de Partida"""
    __tablename__ = "fixtures"
    
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False, index=True)
    season_id = Column(Integer, nullable=False, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    
    home_team_name = Column(String(255), nullable=False)
    away_team_name = Column(String(255), nullable=False)
    
    status = Column(String(50), nullable=False, index=True)
    date_unix = Column(Integer, nullable=True, index=True)
    
    # Placar
    home_goal_count = Column(Integer, default=0)
    away_goal_count = Column(Integer, default=0)
    total_goal_count = Column(Integer, default=0)
    
    # Estatísticas
    home_corners = Column(Integer, default=0)
    away_corners = Column(Integer, default=0)
    home_possession = Column(Integer, default=0)
    away_possession = Column(Integer, default=0)
    home_shots = Column(Integer, default=0)
    away_shots = Column(Integer, default=0)
    home_xg = Column(Float, nullable=True)
    away_xg = Column(Float, nullable=True)
    
    # Cards
    home_yellow_cards = Column(Integer, default=0)
    away_yellow_cards = Column(Integer, default=0)
    home_red_cards = Column(Integer, default=0)
    away_red_cards = Column(Integer, default=0)
    
    # Over/Under
    over05 = Column(Boolean, default=False)
    over15 = Column(Boolean, default=False)
    over25 = Column(Boolean, default=False)
    over35 = Column(Boolean, default=False)
    btts = Column(Boolean, default=False)
    
    stadium_name = Column(String(255), nullable=True)
    
    # Relationships
    league = relationship("League", backref="fixtures")
    home_team = relationship("Team", foreign_keys=[home_team_id], backref="home_fixtures")
    away_team = relationship("Team", foreign_keys=[away_team_id], backref="away_fixtures")
    
    def __repr__(self):
        return (
            f"<Fixture(id={self.id}, {self.home_team_name} vs {self.away_team_name}, "
            f"status='{self.status}')>"
        )

