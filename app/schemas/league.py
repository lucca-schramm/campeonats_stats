"""Schemas de League"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class LeagueBase(BaseModel):
    """Schema base de League"""
    name: str
    country: str
    season_id: int
    season_year: int


class LeagueCreate(LeagueBase):
    """Schema para criação de League"""
    image: Optional[str] = None


class LeagueUpdate(BaseModel):
    """Schema para atualização de League"""
    name: Optional[str] = None
    country: Optional[str] = None
    image: Optional[str] = None
    season_year: Optional[int] = None


class LeagueResponse(LeagueBase):
    """Schema de resposta de League"""
    id: int
    image: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

