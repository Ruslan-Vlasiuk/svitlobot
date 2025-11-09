from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    ADMIN_BOT_TOKEN: str
    TELEGRAM_CHANNEL_ID: int
    TELEGRAM_CHANNEL_USERNAME: str
    ADMIN_USER_IDS: str

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str
    ADMIN_API_TOKEN: str

    # LiqPay
    LIQPAY_PUBLIC_KEY: str
    LIQPAY_PRIVATE_KEY: str
    LIQPAY_CALLBACK_URL: str

    # Prices
    STANDARD_PRICE_1M: int = 50
    STANDARD_PRICE_3M: int = 130
    STANDARD_PRICE_6M: int = 230
    PRO_PRICE_1M: int = 100
    PRO_PRICE_3M: int = 260
    PRO_PRICE_6M: int = 460

    # IoT
    IOT_API_KEY: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION_DAYS: int = 10

    # Other
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    TIMEZONE: str = "Europe/Kiev"
    TEST_MODE: bool = False

    @property
    def admin_user_ids_list(self) -> List[int]:
        return [int(x.strip()) for x in self.ADMIN_USER_IDS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()