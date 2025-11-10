"""
Configuration Settings
Все настройки приложения через переменные окружения
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # PostgreSQL
    POSTGRES_USER: str = "svetlobot_user"
    POSTGRES_PASSWORD: str = "svetlobot_dev_pass_2024"
    POSTGRES_DB: str = "svetlobot"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "redis_dev_pass_2024"
    REDIS_DB: int = 0

    # Celery (используем Redis как broker и backend)
    CELERY_BROKER_URL: str = "redis://:redis_dev_pass_2024@redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://:redis_dev_pass_2024@redis:6379/2"

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Security
    ADMIN_API_TOKEN: str = "dev_admin_token_12345"
    IOT_API_KEY: str = "dev_iot_key_12345"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    ADMIN_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHANNEL_ID: Optional[str] = None
    ADMIN_USER_ID: Optional[int] = None

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    TELEGRAM_RATE_LIMIT: int = 30  # messages per second

    # Notification Settings
    NOTIFICATION_BATCH_SIZE: int = 1000  # пользователей в одном батче
    NOTIFICATION_RETRY_ATTEMPTS: int = 3
    NOTIFICATION_RETRY_DELAY: int = 60  # секунд
    # Debug mode
    DEBUG: bool = False

    # Database URLs
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()