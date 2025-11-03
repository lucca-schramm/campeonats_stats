"""Modelo WebhookLog"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WebhookLog(BaseModel):
    """Modelo de Log de Webhook"""
    __tablename__ = "webhook_logs"
    
    subscription_id = Column(Integer, ForeignKey("webhook_subscriptions.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB, nullable=True)  # PostgreSQL JSONB
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    triggered_at = Column(DateTime, nullable=False)
    
    # Relationships
    subscription = relationship("WebhookSubscription", backref="logs")
    
    def __repr__(self):
        return (
            f"<WebhookLog(id={self.id}, subscription_id={self.subscription_id}, "
            f"event_type='{self.event_type}', response_code={self.response_code})>"
        )

