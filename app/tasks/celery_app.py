"""Configuração do Celery"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    'campeonatos_stats',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Importa todas as tasks para registro automático
# Isso garante que todas as tasks sejam registradas no worker
from app.tasks import scheduler, data_collection, live_monitor  # noqa

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

# Agendamento otimizado
celery_app.conf.beat_schedule = {
    # Verificação de banco vazio - a cada 5 minutos (mais frequente para detectar banco vazio rapidamente)
    'check-empty-database': {
        'task': 'app.tasks.scheduler.check_and_collect_if_empty',
        'schedule': crontab(minute='*/5'),
    },
    # Atualização de partidas ao vivo - a cada 2 minutos (apenas se houver ligas no banco)
    'update-live-matches': {
        'task': 'app.tasks.live_monitor.update_live_matches_task',
        'schedule': crontab(minute='*/2'),
    },
    # Coleta periódica - a cada 6 horas (otimizado para não sobrecarregar API)
    'periodic-collection': {
        'task': 'app.tasks.scheduler.periodic_full_collection',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}

