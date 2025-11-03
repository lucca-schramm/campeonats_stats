"""Modelo League"""
from sqlalchemy import Column, Integer, String, Text
from app.models.base import BaseModel


class League(BaseModel):
    """Modelo de Liga"""
    __tablename__ = "leagues"
    
    name = Column(String(255), nullable=False, index=True)
    country = Column(String(100), nullable=False)
    image = Column(Text, nullable=True)
    season_id = Column(Integer, nullable=False, index=True)
    season_year = Column(Integer, nullable=False)
    
    def __repr__(self):
        return f"<League(id={self.id}, name='{self.name}', season_year={self.season_year})>"

