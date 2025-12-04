"""Endpoints de Webhooks"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.core.database import get_db
from app.schemas.webhook import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse
)
from app.webhooks.manager import WebhookManager
from app.models.webhook_subscription import WebhookSubscription

router = APIRouter()


@router.post("/", response_model=WebhookSubscriptionResponse)
async def create_webhook(
    subscription: WebhookSubscriptionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Registra um novo webhook"""
    webhook_manager = WebhookManager()
    
    # Valida eventos permitidos
    allowed_events = [
        'standings_updated',
        'fixture_updated',
        'fixture_created',
        'top_scorer_updated',
        'team_statistics_updated'
    ]
    
    if not all(e in allowed_events for e in subscription.events):
        raise HTTPException(
            status_code=400,
            detail=f"Eventos inválidos. Permitidos: {allowed_events}"
        )
    
    subscription_id = webhook_manager.register_webhook(
        url=subscription.url,
        league_id=subscription.league_id,
        events=subscription.events
    )
    
    # Busca subscription criada
    result = await db.execute(
        select(WebhookSubscription).filter(
            WebhookSubscription.id == subscription_id
        )
    )
    webhook_sub = result.scalar_one_or_none()
    
    if not webhook_sub:
        raise HTTPException(status_code=404, detail="Webhook não encontrado após criação")
    
    return WebhookSubscriptionResponse.model_validate(webhook_sub)


@router.get("/", response_model=List[WebhookSubscriptionResponse])
async def list_webhooks(
    league_id: Optional[int] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista todos os webhooks"""
    query = select(WebhookSubscription)
    
    if league_id:
        query = query.filter(WebhookSubscription.league_id == league_id)
    
    if active is not None:
        query = query.filter(WebhookSubscription.active == active)
    
    result = await db.execute(query)
    webhooks = result.scalars().all()
    return [WebhookSubscriptionResponse.model_validate(w) for w in webhooks]


@router.get("/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtém um webhook por ID"""
    result = await db.execute(
        select(WebhookSubscription).filter(
            WebhookSubscription.id == webhook_id
        )
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    
    return WebhookSubscriptionResponse.model_validate(webhook)


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove um webhook"""
    result = await db.execute(
        select(WebhookSubscription).filter(
            WebhookSubscription.id == webhook_id
        )
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    
    webhook.active = False
    await db.commit()
    
    return {"message": "Webhook desativado"}


@router.post("/frontend/register")
async def register_frontend_webhook(
    url: str = Body(...),
    events: List[str] = Body(...),
    league_id: Optional[int] = Body(None)
):
    """
    Registra webhook específico para o frontend.
    
    O frontend pode se registrar para receber notificações quando:
    - standings_updated: Tabela atualizada
    - fixture_live_update: Partida ao vivo atualizada
    - top_scorer_updated: Artilharia atualizada
    """
    webhook_manager = WebhookManager()
    subscription_id = webhook_manager.register_webhook(
        url=url,
        league_id=league_id,
        events=events,
        secret=None  # Frontend pode não precisar de validação, ou usar API key
    )
    return {
        "subscription_id": subscription_id,
        "url": url,
        "status": "active"
    }
