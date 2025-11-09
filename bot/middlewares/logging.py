from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для детального логирования всех событий"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем входящее событие
        if isinstance(event, Update):
            if event.message:
                logger.info(f"📨 Message: text='{event.message.text}', from={event.message.from_user.id}")
            elif event.callback_query:
                logger.info(f"🔘 Callback: data='{event.callback_query.data}', from={event.callback_query.from_user.id}")
        
        try:
            # Вызываем handler
            return await handler(event, data)
        except Exception as e:
            logger.error(f"❌ Handler error: {e}", exc_info=True)
            raise
