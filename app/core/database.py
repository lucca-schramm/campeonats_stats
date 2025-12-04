"""Configuração do banco de dados async e sync"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy import create_engine
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

# Converte URL async para sync (remove +asyncpg)
def get_sync_database_url() -> str:
    """Converte URL async para sync"""
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://")
    return url

# Garante que a URL async use asyncpg explicitamente
def get_async_database_url() -> str:
    """Garante URL async com asyncpg"""
    url = settings.database_url
    if not url.startswith("postgresql+asyncpg://"):
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        elif url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return url

# Engine async otimizado (criado primeiro para evitar conflitos)
# Usa asyncpg explicitamente na URL
async_url = get_async_database_url()
if not async_url.startswith("postgresql+asyncpg://"):
    async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    async_url,
    pool_size=20,  # Pool menor para async (mais eficiente)
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
    future=True,
)

# Engine sync para operações síncronas (usado por tasks Celery e scripts)
# Usa psycopg2 explicitamente na URL
sync_url = get_sync_database_url()
if not sync_url.startswith("postgresql+psycopg2://"):
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")

sync_engine = create_engine(
    sync_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

# Session factory async
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Session factory sync (para tasks Celery e scripts)
SessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency async para obter sessão do banco de dados.
    Uso: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Inicializa o banco de dados criando todas as tabelas"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Banco de dados inicializado")


async def close_db():
    """Fecha todas as conexões do banco"""
    await engine.dispose()
    logger.info("Conexões do banco de dados fechadas")

