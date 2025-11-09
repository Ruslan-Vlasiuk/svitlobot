from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, JSON
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    # Основна інформація
    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Підписка
    subscription_tier = Column(
        String(20),
        nullable=False,
        default='NOFREE',
        index=True
    )  # 'NOFREE', 'FREE', 'STANDARD', 'PRO'

    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_channel_subscribed = Column(Boolean, default=False, index=True)
    last_subscription_check = Column(DateTime(timezone=True))

    # Локація
    primary_address_id = Column(Integer, nullable=True)
    address_count = Column(Integer, default=1)  # 1, 2, або 3

    # Реферали
    referred_by = Column(BigInteger, nullable=True, index=True)
    referral_code = Column(String(20), unique=True, index=True)
    referral_count = Column(Integer, default=0)
    referral_days_earned = Column(Integer, default=0)

    # Налаштування сповіщень
    settings = Column(JSON, default={
        "warning_times": [5, 10, 15, 30, 60, 120],
        "notifications_enabled": True,
        "night_mode": False
    })

    # Статистика
    total_notifications_sent = Column(Integer, default=0)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now())
    is_blocked = Column(Boolean, default=False)

    def __repr__(self):
        return f"<User {self.user_id} ({self.subscription_tier})>"