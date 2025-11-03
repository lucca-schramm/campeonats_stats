"""Configuração de logging"""
import logging
import sys
from pathlib import Path
from app.core.config import settings

# Cria diretório de logs se não existir
Path("logs").mkdir(exist_ok=True)


def setup_logging():
    """Configura logging da aplicação"""
    
    # Formato de log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Handlers
    handlers = [
        logging.StreamHandler(sys.stdout)
    ]
    
    # Se não estiver em debug, também loga em arquivo
    if not settings.DEBUG:
        file_handler = logging.FileHandler(
            settings.LOG_FILE,
            encoding="utf-8"
        )
        handlers.append(file_handler)
    
    # Configuração
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    # Reduz verbosidade de bibliotecas externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configurado")
    
    return logger

