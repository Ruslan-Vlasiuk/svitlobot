from pydantic_settings import BaseSettings
from typing import List
import os  # ← ДОДАЙ це


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHANNEL_ID: int
    TELEGRAM_CHANNEL_USERNAME: str
    ADMIN_USER_IDS: str

    # Backend API (ИСПРАВЛЕНО: backend вместо localhost)
    API_BASE_URL: str = "http://backend:8000"

    # Redis (для FSM)
    REDIS_URL: str

    # Другое
    DEBUG: bool = False

    @property
    def admin_user_ids_list(self) -> List[int]:
        return [int(x.strip()) for x in self.ADMIN_USER_IDS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# ✅ ДОДАЙ ЦЕ:
ADMIN_TELEGRAM_IDS = settings.admin_user_ids_list