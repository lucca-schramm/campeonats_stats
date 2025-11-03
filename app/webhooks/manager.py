"""Gerenciador de Webhooks"""
import requests
import json
import hmac
import hashlib
import time
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.webhook_subscription import WebhookSubscription
from app.models.webhook_log import WebhookLog
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WebhookManager:
    """Gerenciador de webhooks"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CampeonatosStats-Webhook/1.0'
        })
        self.session.timeout = settings.WEBHOOK_TIMEOUT
    
    def generate_signature(self, payload: str, secret: str) -> str:
        """Gera assinatura HMAC-SHA256 para validação"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _generate_secret(self) -> str:
        """Gera secret aleatório"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def register_webhook(
        self,
        url: str,
        league_id: Optional[int],
        events: List[str],
        secret: Optional[str] = None
    ) -> int:
        """Registra um novo webhook"""
        db = SessionLocal()
        try:
            subscription = WebhookSubscription(
                url=url,
                league_id=league_id,
                events=events,
                secret=secret or self._generate_secret(),
                active=True
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            logger.info(f"Webhook registrado: {subscription.id} -> {url}")
            return subscription.id
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao registrar webhook: {e}")
            raise
        finally:
            db.close()
    
    def trigger_webhook(
        self,
        event_type: str,
        league_id: int,
        data: Dict
    ):
        """Dispara webhook para todos os subscribers do evento"""
        db = SessionLocal()
        try:
            # Busca subscriptions ativas
            subscriptions = db.query(WebhookSubscription).filter(
                WebhookSubscription.active == True,
                WebhookSubscription.league_id == league_id,
                WebhookSubscription.events.contains([event_type])
            ).all()
            
            for subscription in subscriptions:
                try:
                    payload = {
                        "event": event_type,
                        "league_id": league_id,
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    payload_str = json.dumps(payload)
                    headers = {
                        'X-Webhook-Signature': self.generate_signature(
                            payload_str,
                            subscription.secret or settings.WEBHOOK_SECRET_KEY or ""
                        ),
                        'X-Webhook-Event': event_type,
                        'X-Webhook-Timestamp': str(int(time.time()))
                    }
                    
                    response = self.session.post(
                        subscription.url,
                        json=payload,
                        headers=headers,
                        timeout=settings.WEBHOOK_TIMEOUT
                    )
                    
                    # Log do webhook
                    log = WebhookLog(
                        subscription_id=subscription.id,
                        event_type=event_type,
                        payload=payload,
                        response_code=response.status_code,
                        response_body=response.text[:1000],
                        triggered_at=datetime.utcnow()
                    )
                    db.add(log)
                    
                    subscription.last_triggered_at = datetime.utcnow()
                    
                    if response.status_code >= 400:
                        subscription.failure_count += 1
                        if subscription.failure_count >= 5:
                            subscription.active = False
                            logger.warning(
                                f"Webhook {subscription.id} desativado após 5 falhas"
                            )
                    else:
                        subscription.failure_count = 0
                    
                    db.commit()
                    logger.info(
                        f"Webhook {subscription.id} disparado: "
                        f"{event_type} -> {subscription.url} ({response.status_code})"
                    )
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Erro ao disparar webhook {subscription.id}: {e}")
                    subscription.failure_count += 1
                    db.commit()
                except Exception as e:
                    logger.error(f"Erro inesperado no webhook {subscription.id}: {e}")
                    db.rollback()
                    
        finally:
            db.close()

