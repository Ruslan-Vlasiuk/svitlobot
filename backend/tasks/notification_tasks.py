"""
Notification Tasks
Celery задачи для отправки уведомлений
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, delete
from celery import Task

from celery_app import celery_app
from database import get_session
from models.user import User
from models.notification import Notification
from models.queue import Queue
from services.notification_service import notification_service

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """
    Базовый класс для асинхронных Celery задач
    """

    def __call__(self, *args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self.run_async(*args, **kwargs)
        )

    async def run_async(self, *args, **kwargs):
        raise NotImplementedError()


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="tasks.notification_tasks.send_queue_notification",
    max_retries=3,
    default_retry_delay=60
)
async def send_queue_notification(
        self,
        queue_id: int,
        notification_type: str,
        message_template: str,
        disable_notification: bool = False,
        tier_filter: Optional[List[str]] = None
):
    """
    Отправка уведомления всем пользователям очереди

    Args:
        queue_id: ID очереди
        notification_type: Тип уведомления (power_on, power_off, warning, etc.)
        message_template: Шаблон сообщения
        disable_notification: Тихое уведомление (для ночных часов)
        tier_filter: Фильтр по тарифам (например, ["STANDARD", "PRO"])
    """
    logger.info(f"Task started: send_queue_notification for queue {queue_id}")

    try:
        async with get_session() as session:
            result = await notification_service.send_queue_notification(
                session=session,
                queue_id=queue_id,
                notification_type=notification_type,
                message_template=message_template,
                disable_notification=disable_notification,
                tier_filter=tier_filter
            )

            logger.info(
                f"Task completed: {result['success']} sent, {result['failed']} failed"
            )

            return result

    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="tasks.notification_tasks.send_power_off_notification",
    max_retries=3,
    default_retry_delay=60
)
async def send_power_off_notification(self, queue_id: int):
    """
    Отправка уведомления об отключении света

    Args:
        queue_id: ID очереди
    """
    logger.info(f"Sending power OFF notification to queue {queue_id}")

    # Шаблон сообщения
    message = (
        "⚡️ <b>Відключення світла</b>\n\n"
        "🔴 Світло відключено\n"
        "🔌 Черга: {queue}\n"
        "⏰ Час: {time}\n\n"
        "Ми повідомимо вас, коли світло з'явиться."
    )

    # Определяем тихое уведомление (с 23:00 до 07:00)
    current_hour = datetime.now().hour
    disable_notification = 23 <= current_hour or current_hour < 7

    return await send_queue_notification(
        queue_id=queue_id,
        notification_type="power_off",
        message_template=message,
        disable_notification=disable_notification
    )


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="tasks.notification_tasks.send_power_on_notification",
    max_retries=3,
    default_retry_delay=60
)
async def send_power_on_notification(self, queue_id: int):
    """
    Отправка уведомления о включении света

    Args:
        queue_id: ID очереди
    """
    logger.info(f"Sending power ON notification to queue {queue_id}")

    # Шаблон сообщения
    message = (
        "⚡️ <b>Включення світла</b>\n\n"
        "🟢 Світло з'явилось!\n"
        "🔌 Черга: {queue}\n"
        "⏰ Час: {time}"
    )

    # Определяем тихое уведомление (с 23:00 до 07:00)
    current_hour = datetime.now().hour
    disable_notification = 23 <= current_hour or current_hour < 7

    return await send_queue_notification(
        queue_id=queue_id,
        notification_type="power_on",
        message_template=message,
        disable_notification=disable_notification
    )


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="tasks.notification_tasks.send_warning_notifications",
    max_retries=2,
    default_retry_delay=30
)
async def send_warning_notifications(
        self,
        queue_id: int,
        minutes_before: int,
        scheduled_time: str  # ISO format datetime string
):
    """
    Отправка предупреждений о предстоящем отключении
    Только для пользователей с тарифами STANDARD и PRO

    Args:
        queue_id: ID очереди
        minutes_before: За сколько минут до отключения
        scheduled_time: Время отключения (ISO format)
    """
    logger.info(
        f"Sending warning notifications to queue {queue_id}, "
        f"{minutes_before} min before {scheduled_time}"
    )

    try:
        scheduled_dt = datetime.fromisoformat(scheduled_time)
        time_str = scheduled_dt.strftime("%H:%M")

        message = (
            f"⚠️ <b>Попередження</b>\n\n"
            f"Через {minutes_before} хвилин (о {time_str}) "
            f"заплановане відключення світла.\n\n"
            f"🔌 Черга: {queue_id}\n"
            f"⏰ Час відключення: {time_str}"
        )

        # Отправляем только пользователям с STANDARD и PRO
        return await send_queue_notification(
            queue_id=queue_id,
            notification_type="warning",
            message_template=message,
            disable_notification=False,
            tier_filter=["STANDARD", "PRO"]
        )

    except Exception as exc:
        logger.error(f"Warning notification failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="tasks.notification_tasks.send_custom_notification",
    max_retries=3,
    default_retry_delay=60
)
async def send_custom_notification(
        self,
        queue_id: Optional[int],
        message: str,
        tier_filter: Optional[List[str]] = None,
        user_ids: Optional[List[int]] = None
):
    """
    Отправка кастомного сообщения (для админа)

    Args:
        queue_id: ID очереди (если None, отправляем всем)
        message: Текст сообщения
        tier_filter: Фильтр по тарифам
        user_ids: Список конкретных user_id (если указан, игнорирует queue_id)
    """
    logger.info(f"Sending custom notification to queue {queue_id or 'ALL'}")

    try:
        async with get_session() as session:
            # Если указаны конкретные пользователи
            if user_ids:
                result = await session.execute(
                    select(User).where(
                        User.user_id.in_(user_ids),
                        User.is_active == True,
                        User.is_bot_blocked == False
                    )
                )
                users = result.scalars().all()

                return await notification_service.send_batch(
                    users=users,
                    message_template=message,
                    notification_type="custom",
                    disable_notification=False
                )

            # Если queue_id указан
            elif queue_id:
                return await notification_service.send_queue_notification(
                    session=session,
                    queue_id=queue_id,
                    notification_type="custom",
                    message_template=message,
                    disable_notification=False,
                    tier_filter=tier_filter
                )

            # Отправка всем пользователям
            else:
                query = select(User).where(
                    User.is_active == True,
                    User.is_bot_blocked == False
                )

                if tier_filter:
                    query = query.where(User.subscription_tier.in_(tier_filter))

                result = await session.execute(query)
                users = result.scalars().all()

                return await notification_service.send_batch(
                    users=users,
                    message_template=message,
                    notification_type="custom",
                    disable_notification=False
                )

    except Exception as exc:
        logger.error(f"Custom notification failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="tasks.notification_tasks.cleanup_old_notifications",
)
async def cleanup_old_notifications(self):
    """
    Очистка старых уведомлений (старше 30 дней)
    Запускается раз в день через Celery Beat
    """
    logger.info("Starting cleanup of old notifications")

    try:
        async with get_session() as session:
            # Удаляем уведомления старше 30 дней
            cutoff_date = datetime.utcnow() - timedelta(days=30)

            result = await session.execute(
                delete(Notification).where(Notification.sent_at < cutoff_date)
            )

            deleted_count = result.rowcount
            await session.commit()

            logger.info(f"Cleaned up {deleted_count} old notifications")

            return {"deleted": deleted_count}

    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        raise


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="tasks.notification_tasks.test_notification",
)
async def test_notification(self, user_id: int):
    """
    Тестовая задача для проверки работы Celery

    Args:
        user_id: Telegram ID пользователя
    """
    logger.info(f"Test notification to user {user_id}")

    message = (
        "🧪 <b>Тестове сповіщення</b>\n\n"
        "Це тестове повідомлення від системи СвітлоБот.\n"
        "Celery працює коректно! ✅"
    )

    result = await notification_service.send_message(user_id, message)

    logger.info(f"Test notification result: {result}")

    return result