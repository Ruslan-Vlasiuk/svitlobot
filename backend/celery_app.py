"""
Celery Application Configuration
Конфигурация Celery для фоновых задач СвітлоБот
"""
from celery import Celery
from celery.schedules import crontab
from config import settings

# Создаём экземпляр Celery
celery_app = Celery(
    "svetlobot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.notification_tasks",
    ]
)

# Конфигурация Celery
celery_app.conf.update(
    # Временная зона
    timezone="Europe/Kiev",
    enable_utc=True,
    
    # Сериализация
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Результаты
    result_expires=3600,  # 1 час
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    
    # Производительность
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Повторы при ошибках
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Ограничения
    task_time_limit=300,  # 5 минут максимум на задачу
    task_soft_time_limit=240,  # 4 минуты soft limit
    
    # Логирование
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

# Периодические задачи (Celery Beat)
# Пока оставляем только очистку старых уведомлений
celery_app.conf.beat_schedule = {
    # Очистка старых уведомлений раз в день
    "cleanup-old-notifications": {
        "task": "tasks.notification_tasks.cleanup_old_notifications",
        "schedule": crontab(hour=3, minute=0),  # в 3:00 ночи
    },
}

if __name__ == "__main__":
    celery_app.start()
