from aiogram import Router, F
from aiogram.types import Message
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "⚡ Повідомити про світло")
async def report_button_handler(message: Message):
    """Обработчик кнопки Повідомити про світло"""
    await message.answer(
        "<b>⚡ Повідомити про світло</b>\n\n"
        "🔜 Функція в розробці"
    )