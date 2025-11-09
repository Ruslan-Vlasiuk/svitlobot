from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models.notification import Notification

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


# ============================================
# PYDANTIC SCHEMAS
# ============================================

class NotificationSend(BaseModel):
    queue_id: int
    notification_type: str  # 'power_on', 'power_off', 'warning_60min', ...
    message_text: Optional[str] = None  # Если не указан - возьмём из Excel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    queue_id: int
    notification_type: str
    message_text: str
    sent_at: datetime
    is_delivered: bool
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


# ============================================
# ENDPOINTS
# ============================================

@router.post("/send")
async def send_notification(
    notif_data: NotificationSend,
    db: AsyncSession = Depends(get_db)
):
    """
    Отправить уведомление всем пользователям черги
    
    Этот endpoint запускает Celery task для массовой рассылки.
    Сама отправка происходит асинхронно.
    
    **Типы уведомлений:**
    - power_on - Свет включился
    - power_off - Свет выключился
    - warning_60min - За 60 мин до отключения
    - warning_30min - За 30 мин до отключения
    - warning_15min - За 15 мин до отключения
    - warning_5min - За 5 мин до отключения
    - insight - Инсайд от администрации (только PRO)
    - pro_voltage_alert - Критическая напряжение (только PRO)
    """
    
    # Валидация queue_id
    if notif_data.queue_id < 1 or notif_data.queue_id > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Queue ID must be between 1 and 12"
        )
    
    # TODO: Запустить Celery task
    # from tasks.notification_dispatcher import send_mass_notification
    # task = send_mass_notification.delay(
    #     queue_id=notif_data.queue_id,
    #     notification_type=notif_data.notification_type,
    #     message_text=notif_data.message_text
    # )
    
    # Пока что просто возвращаем информацию
    return {
        "status": "queued",
        "queue_id": notif_data.queue_id,
        "notification_type": notif_data.notification_type,
        "message": f"Notification queued for queue {notif_data.queue_id}",
        # "task_id": task.id  # ID Celery task
    }


@router.get("/history")
async def get_notification_history(
    user_id: Optional[int] = None,
    queue_id: Optional[int] = None,
    notification_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю уведомлений
    
    Можно фильтровать по:
    - user_id - Конкретный пользователь
    - queue_id - Конкретная черга
    - notification_type - Тип уведомления
    
    **Используется для:**
    - Админ-панели (статистика)
    - Отладки
    - Логирования
    """
    query = select(Notification).order_by(Notification.sent_at.desc())
    
    if user_id:
        query = query.where(Notification.user_id == user_id)
    
    if queue_id:
        query = query.where(Notification.queue_id == queue_id)
    
    if notification_type:
        query = query.where(Notification.notification_type == notification_type)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "queue_id": n.queue_id,
            "notification_type": n.notification_type,
            "sent_at": n.sent_at,
            "is_delivered": n.is_delivered,
            "error_message": n.error_message
        }
        for n in notifications
    ]


@router.get("/stats")
async def get_notification_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Статистика по уведомлениям
    
    Используется для:
    - Админ-панели
    - Мониторинга
    - Графиков
    """
    # Всего уведомлений
    result = await db.execute(select(Notification))
    all_notifs = result.scalars().all()
    
    # Статистика по типам
    by_type = {}
    by_queue = {}
    delivered_count = 0
    failed_count = 0
    
    for n in all_notifs:
        # По типам
        if n.notification_type not in by_type:
            by_type[n.notification_type] = 0
        by_type[n.notification_type] += 1
        
        # По чергам
        if n.queue_id not in by_queue:
            by_queue[n.queue_id] = 0
        by_queue[n.queue_id] += 1
        
        # Доставка
        if n.is_delivered:
            delivered_count += 1
        else:
            failed_count += 1
    
    return {
        "total_sent": len(all_notifs),
        "delivered": delivered_count,
        "failed": failed_count,
        "delivery_rate": f"{(delivered_count / len(all_notifs) * 100):.2f}%" if all_notifs else "0%",
        "by_type": by_type,
        "by_queue": by_queue
    }


@router.post("/test/{user_id}")
async def send_test_notification(
    user_id: int,
    notification_type: str = "power_off",
    db: AsyncSession = Depends(get_db)
):
    """
    Отправить тестовое уведомление одному пользователю
    
    Используется для:
    - Отладки
    - Тестирования шаблонов
    """
    # Проверить, существует ли пользователь
    from models.user import User
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # TODO: Отправить тестовое уведомление через Telegram Bot
    # await bot.send_message(user_id, "🔴 Тестовое уведомление...")
    
    # Сохранить в БД
    notification = Notification(
        user_id=user_id,
        queue_id=1,  # Тестовая черга
        notification_type=f"test_{notification_type}",
        message_text=f"🔴 Тестовое уведомление ({notification_type})",
        is_delivered=True
    )
    
    db.add(notification)
    await db.commit()
    
    return {
        "status": "sent",
        "user_id": user_id,
        "notification_type": notification_type,
        "message": "Test notification sent"
    }


@router.delete("/cleanup")
async def cleanup_old_notifications(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить старые уведомления (>30 дней)
    
    Используется для:
    - Очистки БД
    - Периодического обслуживания (Celery cron task)
    """
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(Notification).where(Notification.sent_at < cutoff_date)
    )
    old_notifs = result.scalars().all()
    
    count = len(old_notifs)
    
    for n in old_notifs:
        await db.delete(n)
    
    await db.commit()
    
    return {
        "status": "cleaned",
        "deleted_count": count,
        "cutoff_date": cutoff_date,
        "message": f"Deleted {count} notifications older than {days} days"
    }
