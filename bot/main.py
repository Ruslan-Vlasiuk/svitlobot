import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from config import settings
from api_client import api_client
from handlers import start, info, user_settings, report, admin_callbacks

# ❌ ВИДАЛИТИ ЦЕЙ РЯДОК (дублікат):
# from handlers import start, info

# Импорт middleware
from middlewares.logging import LoggingMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    logger.info("🤖 Starting СвітлоБот...")

    # Создать бота
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, parse_mode="HTML")

    # Создать storage для FSM (Redis)
    storage = RedisStorage.from_url(settings.REDIS_URL)

    # Создать dispatcher
    dp = Dispatcher(storage=storage)

    # Подключить middleware для логирования
    dp.update.middleware(LoggingMiddleware())

    # Зарегистрировать роутеры
    dp.include_router(start.router)
    dp.include_router(info.router)
    dp.include_router(user_settings.router)
    dp.include_router(report.router)
    dp.include_router(admin_callbacks.router)  # ✅ ДОДАТИ ЦЕЙ РЯДОК

    admin_callbacks.set_api_client(api_client)

    # Удалить webhook (если был установлен)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("✅ Bot started successfully!")

    try:
        bot_info = await bot.get_me()
        logger.info(f"📱 Bot username: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")

    try:
        # Запустить polling
        await dp.start_polling(bot)
    finally:
        # Закрыть соединения
        await api_client.close()
        await bot.session.close()
        logger.info("🛑 Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")