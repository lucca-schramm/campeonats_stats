"""Modelo base para todos os models"""
from sqlalchemy import Column, Integer, DateTime, func
from app.core.database import Base


class BaseModel(Base):
    """Classe base abstrata para todos os modelos"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

