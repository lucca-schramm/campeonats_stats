"""Endpoints de Chatbot"""
from fastapi import APIRouter, HTTPException, Body, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.database import get_db
from app.schemas.chatbot import (
    ChatMessage,
    ChatResponse,
    ChatSession,
    LeagueSearchResponse
)
from app.chatbot.service import ChatbotService
from app.core.cache import cache
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

chat_sessions = {}


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("100/minute")  # Rate limit para chatbot
async def chat_with_bot(request: Request, message: ChatMessage, db: AsyncSession = Depends(get_db)):
    """
    Endpoint principal para chat com bot usando RAG.
    
    O frontend envia mensagens aqui e recebe respostas baseadas em dados do banco.
    Mantém sessão para contexto conversacional.
    """
    try:
        # Cria ou recupera sessão
        session_id = message.session_id or str(uuid.uuid4())
        
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "message_count": 0
            }
        
        chat_sessions[session_id]["message_count"] += 1
        
        # Determina tipo de chatbot
        chatbot_type = message.chatbot_type or "rag"
        if chatbot_type not in ["simple", "rag", "llm"]:
            chatbot_type = "rag"  # Default para RAG
        
        # Processa mensagem
        if chatbot_type == "rag" or chatbot_type == "llm":
            # Usa RAG Service (async) com histórico conversacional
            try:
                from app.chatbot.rag_service import RAGService
                rag_service = RAGService()
                response_text = await rag_service.process_query(message.message, db, session_id=session_id)
            except Exception as e:
                logger.error(f"Erro no RAG, usando fallback: {e}", exc_info=True)
                # Fallback para simple
                chatbot_service = ChatbotService()
                response_text = chatbot_service.process_message(message.message, chatbot_type="simple")
        else:
            # Usa chatbot simples
            chatbot_service = ChatbotService()
            response_text = chatbot_service.process_message(message.message, chatbot_type=chatbot_type)
        
        # Gera sugestões
        suggestions = _generate_suggestions(response_text, message.message)
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat(),
            suggestions=suggestions
        )
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao processar mensagem: {str(e)}")


@router.get("/session/{session_id}", response_model=ChatSession)
async def get_session(session_id: str):
    """Obtém informações de uma sessão de chat"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    session_data = chat_sessions[session_id]
    return ChatSession(
        session_id=session_id,
        created_at=session_data["created_at"],
        message_count=session_data["message_count"]
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Remove uma sessão de chat e limpa histórico"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    
    # Limpa histórico do RAG service
    try:
        from app.chatbot.rag_service import RAGService
        rag_service = RAGService()
        rag_service.clear_conversation_history(session_id)
    except:
        pass
    
    return {"message": "Sessão removida"}


@router.get("/leagues/search", response_model=LeagueSearchResponse)
async def search_leagues(
    q: Optional[str] = None, 
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint auxiliar para busca de ligas.
    Frontend pode usar para autocompletar ou sugerir ligas.
    """
    from app.services.league_service import LeagueService
    
    cache_key = f"leagues:search:{q or ''}:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        # Se cache retornou dict, converte para objeto
        if isinstance(cached_result, dict):
            return LeagueSearchResponse(**cached_result)
        return cached_result
    
    service = LeagueService(db)
    if not q:
        leagues = service.get_all_leagues(limit=limit)
    else:
        leagues = service.search_leagues(q, limit)
    
    result = LeagueSearchResponse(
        leagues=[{"id": l.id, "name": l.name, "country": l.country} for l in leagues]
    )
    
    # Cache como dict para serialização
    cache.set(cache_key, result.model_dump(), ttl=120)
    return result


def _generate_suggestions(response: str, user_message: str) -> list[str]:
    """Gera sugestões de próximas perguntas baseado no contexto"""
    suggestions = []
    message_lower = user_message.lower()
    
    if "classificação" in response or "tabela" in message_lower:
        suggestions.extend([
            "Quem são os artilheiros?",
            "Qual time está em primeiro?",
            "Mostrar estatísticas do time"
        ])
    
    if "artilh" in response or "goleador" in message_lower:
        suggestions.extend([
            "Mostrar tabela de classificação",
            "Estatísticas dos jogadores",
            "Próximas partidas"
        ])
    
    if not suggestions:
        suggestions.extend([
            "Buscar liga Brasileirão",
            "Tabela de classificação",
            "Top artilheiros",
            "Próximas partidas"
        ])
    
    return suggestions[:3]

