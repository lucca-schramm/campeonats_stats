"""Modelo WebhookSubscription"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WebhookSubscription(BaseModel):
    """Modelo de Subscription de Webhook"""
    __tablename__ = "webhook_subscriptions"
    
    url = Column(Text, nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=True, index=True)
    events = Column(PG_ARRAY(String), nullable=False)  # Array de eventos
    secret = Column(String(255), nullable=True)
    active = Column(Boolean, default=True, nullable=False, index=True)
    last_triggered_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    league = relationship("League", backref="webhook_subscriptions")
    
    def __repr__(self):
        return f"<WebhookSubscription(id={self.id}, url='{self.url[:50]}...', active={self.active})>"

