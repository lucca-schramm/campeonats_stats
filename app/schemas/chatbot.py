"""Schemas de Chatbot"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChatMessage(BaseModel):
    """Schema para mensagem de chat"""
    message: str
    session_id: Optional[str] = None
    chatbot_type: Optional[str] = "simple"  # "simple" ou "llm"


class ChatResponse(BaseModel):
    """Schema de resposta do chatbot"""
    response: str
    session_id: str
    timestamp: str
    suggestions: Optional[List[str]] = None


class ChatSession(BaseModel):
    """Schema de sessão de chat"""
    session_id: str
    created_at: str
    message_count: int


class LeagueSearchResponse(BaseModel):
    """Schema de resposta de busca de ligas"""
    leagues: List[dict]

