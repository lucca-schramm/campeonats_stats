"""Configuração do banco de dados"""
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=50,  # Aumentado para suportar alta carga (100k reqs/dia)
    max_overflow=100,  # Máximo de conexões extras durante picos
    pool_pre_ping=True,  # Verifica conexões antes de usar
    pool_recycle=3600,  # Recicla conexões após 1 hora
    pool_reset_on_return='commit',  # Otimiza retorno de conexões
    echo=settings.DEBUG,  # Log SQL em debug
    future=True,
    connect_args={
        "connect_timeout": 10,
        "application_name": "campeonatos_stats_api"
    }
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)


def get_db():
    """
    Dependency para obter sessão do banco de dados.
    Uso: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializa o banco de dados criando todas as tabelas"""
    Base.metadata.create_all(bind=engine)
    logger.info("Banco de dados inicializado")


def close_db():
    """Fecha todas as conexões do banco"""
    engine.dispose()
    logger.info("Conexões do banco de dados fechadas")

