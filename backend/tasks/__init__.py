"""
Tasks package for Celery background jobs
"""

# Импортируем только задачи уведомлений (остальные задачи будут добавлены позже)
from .notification_tasks import (
    send_queue_notification,
    send_power_off_notification,
    send_power_on_notification,
    send_warning_notifications,
    send_custom_notification,
    cleanup_old_notifications,
    test_notification,
)

__all__ = [
    # Notification tasks
    "send_queue_notification",
    "send_power_off_notification",
    "send_power_on_notification",
    "send_warning_notifications",
    "send_custom_notification",
    "cleanup_old_notifications",
    "test_notification",
]