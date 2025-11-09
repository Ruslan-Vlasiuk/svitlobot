from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models.queue import Queue
from models.user import User

router = APIRouter(prefix="/api/queues", tags=["Queues"])


# ============================================
# PYDANTIC SCHEMAS
# ============================================

class QueueResponse(BaseModel):
    queue_id: int
    name: str
    is_power_on: bool
    last_change_at: Optional[datetime]
    last_change_source: Optional[str]
    total_outages: int
    total_uptime_minutes: int
    
    class Config:
        from_attributes = True


class QueueStatusUpdate(BaseModel):
    is_power_on: bool
    source: str  # 'iot', 'crowdreport', 'manual'


# ============================================
# ENDPOINTS
# ============================================

@router.get("/", response_model=List[QueueResponse])
async def get_all_queues(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех черг (1-12)
    """
    result = await db.execute(
        select(Queue).order_by(Queue.queue_id)
    )
    queues = result.scalars().all()
    
    return queues


@router.get("/{queue_id}", response_model=QueueResponse)
async def get_queue(
    queue_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о конкретной черге
    """
    if queue_id < 1 or queue_id > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Queue ID must be between 1 and 12"
        )
    
    result = await db.execute(
        select(Queue).where(Queue.queue_id == queue_id)
    )
    queue = result.scalar_one_or_none()
    
    if not queue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queue {queue_id} not found"
        )
    
    return queue


@router.get("/{queue_id}/status")
async def get_queue_status(
    queue_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить текущий статус черги (ON/OFF)
    
    Возвращает упрощённую информацию для быстрого запроса
    """
    result = await db.execute(
        select(Queue).where(Queue.queue_id == queue_id)
    )
    queue = result.scalar_one_or_none()
    
    if not queue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queue {queue_id} not found"
        )
    
    return {
        "queue_id": queue.queue_id,
        "is_power_on": queue.is_power_on,
        "last_change_at": queue.last_change_at,
        "source": queue.last_change_source
    }


@router.patch("/{queue_id}/status")
async def update_queue_status(
    queue_id: int,
    status_data: QueueStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить статус черги (ON/OFF)
    
    Используется:
    - IoT сенсорами
    - Краудрепортами
    - Админом (ручное управление)
    """
    result = await db.execute(
        select(Queue).where(Queue.queue_id == queue_id)
    )
    queue = result.scalar_one_or_none()
    
    if not queue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queue {queue_id} not found"
        )
    
    # Проверить, изменился ли статус
    status_changed = queue.is_power_on != status_data.is_power_on
    
    if status_changed:
        # Обновить статус
        queue.is_power_on = status_data.is_power_on
        queue.last_change_at = datetime.utcnow()
        queue.last_change_source = status_data.source
        
        # Увеличить счётчик отключений
        if not status_data.is_power_on:
            queue.total_outages += 1
        
        await db.commit()
        
        # TODO: Trigger notification task (Celery)
        # from tasks.notification_dispatcher import send_power_notification
        # send_power_notification.delay(queue_id, status_data.is_power_on)
        
        return {
            "queue_id": queue_id,
            "status_changed": True,
            "new_status": "ON" if status_data.is_power_on else "OFF",
            "message": f"Queue {queue_id} status updated to {'ON' if status_data.is_power_on else 'OFF'}"
        }
    else:
        return {
            "queue_id": queue_id,
            "status_changed": False,
            "message": f"Queue {queue_id} is already {'ON' if queue.is_power_on else 'OFF'}"
        }


@router.get("/{queue_id}/users-count")
async def get_queue_users_count(
    queue_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить количество пользователей в черге
    
    Полезно для:
    - Статистики
    - Планирования массовых рассылок
    """
    # Импортируем Address здесь, чтобы избежать circular import
    from models.address import Address
    
    # Получить все адреса черги
    result = await db.execute(
        select(Address.id).where(Address.queue_id == queue_id)
    )
    address_ids = [row[0] for row in result.all()]
    
    # Подсчитать пользователей с этими адресами
    result = await db.execute(
        select(User).where(User.primary_address_id.in_(address_ids))
    )
    users = result.scalars().all()
    
    # Статистика по тарифам
    tier_counts = {
        'NOFREE': 0,
        'FREE': 0,
        'STANDARD': 0,
        'PRO': 0
    }
    
    for user in users:
        tier_counts[user.subscription_tier] += 1
    
    return {
        "queue_id": queue_id,
        "total_users": len(users),
        "by_tier": tier_counts
    }


@router.get("/status/all")
async def get_all_statuses(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статусы всех черг
    
    Полезно для:
    - Дашборда админа
    - Карты отключений
    - Статистики в канале
    """
    result = await db.execute(
        select(Queue).order_by(Queue.queue_id)
    )
    queues = result.scalars().all()
    
    statuses = []
    power_on_count = 0
    
    for queue in queues:
        statuses.append({
            "queue_id": queue.queue_id,
            "is_power_on": queue.is_power_on,
            "last_change": queue.last_change_at
        })
        if queue.is_power_on:
            power_on_count += 1
    
    return {
        "total_queues": len(queues),
        "power_on_count": power_on_count,
        "power_off_count": len(queues) - power_on_count,
        "queues": statuses
    }
