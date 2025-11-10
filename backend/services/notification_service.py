"""
Notification Service
Сервис для управления и отправки уведомлений пользователям
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from models.user import User
from models.notification import Notification
from models.queue import Queue
from config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Сервис для отправки уведомлений через Telegram Bot API
    """

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.rate_limit = settings.TELEGRAM_RATE_LIMIT  # 30 msg/sec

    async def send_message(
            self,
            user_id: int,
            text: str,
            parse_mode: str = "HTML",
            disable_notification: bool = False,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Отправка одного сообщения пользователю

        Args:
            user_id: Telegram ID пользователя
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
            disable_notification: Тихое уведомление
            **kwargs: Дополнительные параметры (reply_markup, etc.)

        Returns:
            dict: Результат отправки
        """
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": user_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
            **kwargs
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()

                if result.get("ok"):
                    logger.info(f"Message sent to {user_id}")
                    return {"success": True, "message_id": result["result"]["message_id"]}
                else:
                    logger.error(f"Failed to send message to {user_id}: {result}")
                    return {"success": False, "error": result.get("description")}

        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending message to {user_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def send_batch(
            self,
            users: List[User],
            message_template: str,
            notification_type: str,
            disable_notification: bool = False
    ) -> Dict[str, Any]:
        """
        Массовая отправка сообщений батчами с соблюдением rate limit

        Args:
            users: Список пользователей
            message_template: Шаблон сообщения (может содержать {placeholders})
            notification_type: Тип уведомления (power_on, power_off, warning, etc.)
            disable_notification: Тихое уведомление

        Returns:
            dict: Статистика отправки
        """
        total = len(users)
        success = 0
        failed = 0
        errors = []

        logger.info(f"Starting batch send to {total} users, type: {notification_type}")

        # Разбиваем на батчи
        batch_size = settings.NOTIFICATION_BATCH_SIZE

        for i in range(0, total, batch_size):
            batch = users[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} users)")

            # Создаём задачи для параллельной отправки
            tasks = []
            for user in batch:
                # Форматируем сообщение под конкретного пользователя
                message = self._format_message(message_template, user)

                # Создаём задачу отправки
                task = self.send_message(
                    user_id=user.user_id,
                    text=message,
                    disable_notification=disable_notification
                )
                tasks.append(task)

            # Отправляем батч параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Подсчитываем результаты
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    failed += 1
                    errors.append({
                        "user_id": batch[idx].user_id,
                        "error": str(result)
                    })
                elif result.get("success"):
                    success += 1
                else:
                    failed += 1
                    errors.append({
                        "user_id": batch[idx].user_id,
                        "error": result.get("error", "Unknown error")
                    })

            # Rate limiting: 30 msg/sec = задержка между батчами
            if i + batch_size < total:
                delay = len(batch) / self.rate_limit
                logger.info(f"Rate limit delay: {delay:.2f}s")
                await asyncio.sleep(delay)

        logger.info(f"Batch send completed: {success} success, {failed} failed")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors[:10]  # Возвращаем только первые 10 ошибок
        }

    async def send_queue_notification(
            self,
            session: AsyncSession,
            queue_id: int,
            notification_type: str,
            message_template: str,
            disable_notification: bool = False,
            tier_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Отправка уведомления всем пользователям очереди

        Args:
            session: Database session
            queue_id: ID очереди
            notification_type: Тип уведомления
            message_template: Шаблон сообщения
            disable_notification: Тихое уведомление
            tier_filter: Фильтр по тарифам (например, ["STANDARD", "PRO"])

        Returns:
            dict: Статистика отправки
        """
        logger.info(f"Sending notification to queue {queue_id}, type: {notification_type}")

        # Получаем пользователей очереди
        users = await self._get_queue_users(
            session,
            queue_id,
            notification_type,
            tier_filter
        )

        if not users:
            logger.warning(f"No users found for queue {queue_id}")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "errors": []
            }

        # Сохраняем уведомление в БД
        notification = Notification(
            queue_id=queue_id,
            notification_type=notification_type,
            message=message_template,
            sent_at=datetime.utcnow()
        )
        session.add(notification)
        await session.commit()

        # Отправляем батчами
        result = await self.send_batch(
            users=users,
            message_template=message_template,
            notification_type=notification_type,
            disable_notification=disable_notification
        )

        # Обновляем статистику уведомления
        notification.users_sent = result["success"]
        notification.users_failed = result["failed"]
        await session.commit()

        return result

    async def _get_queue_users(
            self,
            session: AsyncSession,
            queue_id: int,
            notification_type: str,
            tier_filter: Optional[List[str]] = None
    ) -> List[User]:
        """
        Получить список пользователей очереди с фильтрацией

        Args:
            session: Database session
            queue_id: ID очереди
            notification_type: Тип уведомления (для проверки настроек)
            tier_filter: Фильтр по тарифам

        Returns:
            List[User]: Список пользователей
        """
        # Базовый запрос
        query = select(User).where(
            User.primary_queue_id == queue_id,
            User.is_active == True,
            User.is_bot_blocked == False
        )

        # Фильтр по тарифам
        if tier_filter:
            query = query.where(User.subscription_tier.in_(tier_filter))

        result = await session.execute(query)
        users = result.scalars().all()

        # Дополнительная фильтрация по настройкам уведомлений
        filtered_users = []
        for user in users:
            if self._can_receive_notification(user, notification_type):
                filtered_users.append(user)

        return filtered_users

    def _can_receive_notification(self, user: User, notification_type: str) -> bool:
        """
        Проверить, может ли пользователь получить уведомление данного типа

        Args:
            user: Пользователь
            notification_type: Тип уведомления

        Returns:
            bool: Может ли получить уведомление
        """
        settings = user.notification_settings or {}

        # Проверяем настройки для конкретного типа
        if notification_type == "power_off":
            return settings.get("power_off_enabled", True)
        elif notification_type == "power_on":
            return settings.get("power_on_enabled", True)
        elif notification_type == "warning":
            return settings.get("warnings_enabled", False) and user.subscription_tier in ["STANDARD", "PRO"]
        elif notification_type == "schedule":
            return settings.get("schedule_enabled", False) and user.subscription_tier == "PRO"

        # По умолчанию разрешаем
        return True

    def _format_message(self, template: str, user: User) -> str:
        """
        Форматировать сообщение под конкретного пользователя

        Args:
            template: Шаблон сообщения
            user: Пользователь

        Returns:
            str: Отформатированное сообщение
        """
        try:
            # Доступные плейсхолдеры
            placeholders = {
                "first_name": user.first_name or "Користувач",
                "username": user.username or "",
                "queue": user.primary_queue_id or "невідомо",
                "time": datetime.now().strftime("%H:%M"),
                "date": datetime.now().strftime("%d.%m.%Y"),
            }

            return template.format(**placeholders)
        except KeyError as e:
            logger.warning(f"Missing placeholder {e} in template, using raw template")
            return template

    async def send_warning_notification(
            self,
            session: AsyncSession,
            user_id: int,
            queue_id: int,
            minutes_before: int,
            scheduled_time: datetime
    ) -> Dict[str, Any]:
        """
        Отправка предупреждения о предстоящем отключении

        Args:
            session: Database session
            user_id: Telegram ID пользователя
            queue_id: ID очереди
            minutes_before: За сколько минут до отключения
            scheduled_time: Запланированное время отключения

        Returns:
            dict: Результат отправки
        """
        # Получаем пользователя
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return {"success": False, "error": "User not found"}

        # Формируем сообщение
        time_str = scheduled_time.strftime("%H:%M")
        message = (
            f"⚠️ <b>Попередження</b>\n\n"
            f"Через {minutes_before} хвилин (о {time_str}) заплановане відключення світла.\n\n"
            f"🔌 Черга: {queue_id}\n"
            f"⏰ Час відключення: {time_str}"
        )

        # Отправляем
        return await self.send_message(user_id, message)


# Глобальный экземпляр сервиса
notification_service = NotificationService()