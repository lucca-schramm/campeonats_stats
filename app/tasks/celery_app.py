"""Configuração do Celery"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    'campeonatos_stats',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_max_tasks_per_child=50,
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Configura agendamento a cada 15 minutos (registrado diretamente aqui para evitar circular import)
celery_app.conf.beat_schedule = {
    'collect-data-every-15min': {
        'task': 'app.tasks.scheduler.scheduled_collection',
        'schedule': crontab(minute='*/15'),
    },
}

