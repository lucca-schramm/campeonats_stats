"""Schemas de Webhook"""
from pydantic import BaseModel, HttpUrl, ConfigDict
from typing import Optional, List
from datetime import datetime


class WebhookSubscriptionCreate(BaseModel):
    """Schema para criar subscription de webhook"""
    url: str
    league_id: Optional[int] = None
    events: List[str]


class WebhookSubscriptionResponse(BaseModel):
    """Schema de resposta de subscription"""
    id: int
    url: str
    league_id: Optional[int] = None
    events: List[str]
    active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class WebhookPayload(BaseModel):
    """Schema do payload enviado no webhook"""
    event: str
    league_id: int
    data: dict
    timestamp: str

