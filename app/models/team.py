"""Modelo Team"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Team(BaseModel):
    """Modelo de Time"""
    __tablename__ = "teams"
    
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False, index=True)
    season_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    clean_name = Column(String(255), nullable=True)
    english_name = Column(String(255), nullable=True)
    short_hand = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    continent = Column(String(50), nullable=True)
    founded = Column(String(10), nullable=True)
    image = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    table_position = Column(Integer, nullable=True)
    performance_rank = Column(Integer, nullable=True)
    
    # Relationships
    league = relationship("League", backref="teams")
    
    __table_args__ = (
        UniqueConstraint('id', 'league_id', 'season_id', name='uq_team_league_season'),
    )
    
    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}', league_id={self.league_id})>"

