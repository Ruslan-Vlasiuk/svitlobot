"""
Головний файл Telegram бота СвітлоБот
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.enums import ParseMode

from config import settings
from handlers import start, info, user_settings, report, admin_callbacks, crowdreport

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота"""
    try:
        logger.info("🤖 Starting СвітлоБот...")

        # Створити бота
        bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            parse_mode=ParseMode.HTML
        )

        # Створити storage для FSM
        storage = RedisStorage.from_url(settings.REDIS_URL)

        # Створити dispatcher
        dp = Dispatcher(storage=storage)

        # Реєстрація роутерів
        dp.include_router(start.router)
        dp.include_router(info.router)
        dp.include_router(user_settings.router)
        dp.include_router(report.router)
        dp.include_router(admin_callbacks.router)
        dp.include_router(crowdreport.router)

        logger.info("✅ Bot started successfully!")

        # Отримати інфо про бота
        bot_info = await bot.get_me()
        logger.info(f"📱 Bot username: @{bot_info.username}")

        # Видалити webhook і запустити polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()
        logger.info("🛑 Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")