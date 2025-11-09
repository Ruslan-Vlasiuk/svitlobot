from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import hashlib
import base64

from database import get_db
from models.user import User

router = APIRouter(prefix="/api/users", tags=["Users"])


# ============================================
# PYDANTIC SCHEMAS
# ============================================

class UserCreate(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    referral_code_used: Optional[str] = None  # Реферальный код при регистрации


class UserUpdate(BaseModel):
    primary_address_id: Optional[int] = None
    subscription_tier: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    is_channel_subscribed: Optional[bool] = None
    settings: Optional[dict] = None


class UserResponse(BaseModel):
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    created_at: datetime
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    is_channel_subscribed: bool
    primary_address_id: Optional[int]
    referral_code: str
    referral_count: int
    referral_days_earned: int
    
    class Config:
        from_attributes = True


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_referral_code(user_id: int) -> str:
    """Генерация уникального реферального кода"""
    # Создаём хеш из user_id + соль
    raw = f"{user_id}_{user_id * 12345}"
    hash_obj = hashlib.sha256(raw.encode())
    hash_hex = hash_obj.hexdigest()[:12]
    
    # Конвертируем в base64 для читабельности
    b64 = base64.urlsafe_b64encode(hash_hex.encode()).decode()[:10]
    
    return f"REF_{b64}"


# ============================================
# ENDPOINTS
# ============================================

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание нового пользователя (регистрация)
    
    - **user_id**: Telegram user ID
    - **username**: Telegram username (опционально)
    - **first_name**: Имя пользователя
    - **referral_code_used**: Реферальный код (если использовал)
    """
    
    # 1. Проверить, существует ли пользователь
    result = await db.execute(
        select(User).where(User.user_id == user_data.user_id)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Пользователь уже существует
        return existing_user
    
    # 2. Найти реферера (если указан код)
    referrer_id = None
    if user_data.referral_code_used:
        result = await db.execute(
            select(User).where(User.referral_code == user_data.referral_code_used)
        )
        referrer = result.scalar_one_or_none()
        if referrer:
            referrer_id = referrer.user_id
    
    # 3. Создать нового пользователя
    new_user = User(
        user_id=user_data.user_id,
        username=user_data.username,
        first_name=user_data.first_name,
        referred_by=referrer_id,
        referral_code=generate_referral_code(user_data.user_id),
        subscription_tier='NOFREE',  # Начальный тариф
        is_channel_subscribed=False
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 4. Если был реферер - обработаем это позже в referrals.py
    # (после того как пользователь определит адрес)
    
    return new_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о пользователе
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить данные пользователя
    
    Используется для:
    - Установки адреса (primary_address_id)
    - Изменения тарифа (subscription_tier)
    - Обновления подписки на канал (is_channel_subscribed)
    - Изменения настроек уведомлений (settings)
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Обновить поля (только те, что переданы)
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    # Обновить last_active_at
    user.last_active_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/{user_id}/check-subscription")
async def check_channel_subscription(
    user_id: int,
    is_subscribed: bool,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить статус подписки на канал
    
    Вызывается после проверки через Telegram API
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Обновить статус подписки
    user.is_channel_subscribed = is_subscribed
    user.last_subscription_check = datetime.utcnow()
    
    # Если подписался - изменить тариф с NOFREE на FREE
    if is_subscribed and user.subscription_tier == 'NOFREE':
        user.subscription_tier = 'FREE'
    
    await db.commit()
    
    return {
        "user_id": user_id,
        "is_subscribed": is_subscribed,
        "subscription_tier": user.subscription_tier,
        "message": "Subscription status updated"
    }


@router.get("/{user_id}/referral-stats")
async def get_referral_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику по рефералам
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Получить список рефералов
    result = await db.execute(
        select(User).where(User.referred_by == user_id)
    )
    referrals = result.scalars().all()
    
    return {
        "user_id": user_id,
        "referral_code": user.referral_code,
        "referral_count": user.referral_count,
        "referral_days_earned": user.referral_days_earned,
        "referral_link": f"https://t.me/svetlobot_irpin?start=ref_{user.referral_code}",
        "referrals": [
            {
                "user_id": ref.user_id,
                "username": ref.username,
                "created_at": ref.created_at
            }
            for ref in referrals
        ]
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить пользователя (мягкое удаление)
    
    НЕ удаляет из БД, а помечает как заблокированного
    """
    result = await db.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Мягкое удаление
    user.is_blocked = True
    user.primary_address_id = None
    user.referred_by = None
    
    await db.commit()
    
    return {
        "user_id": user_id,
        "message": "User deleted (soft delete)"
    }
