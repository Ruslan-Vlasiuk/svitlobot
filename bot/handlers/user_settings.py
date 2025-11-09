from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

from api_client import api_client
from keyboards.inline import get_subscription_keyboard  # Используем существующую


logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "⚙️ Налаштування")
async def settings_button_handler(message: Message):
    """Обработчик кнопки Налаштування из главного меню"""
    user_id = message.from_user.id

    try:
        user = await api_client.get_user(user_id)

        await message.answer(
            "<b>⚙️ Налаштування</b>\n\n"
            f"👤 Користувач: {message.from_user.first_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📋 Тариф: {user.get('subscription_tier', 'FREE')}\n\n"
            "Оберіть розділ:",
            reply_markup=get_settings_keyboard()
        )
    except Exception as e:
        logger.error(f"Error loading settings for {user_id}: {e}")
        await message.answer(
            "⚙️ Налаштування\n\n"
            "🔜 Функція в розробці"
        )


@router.callback_query(F.data == "settings_back")
async def settings_back(callback: CallbackQuery):
    """Повернутися до налаштувань"""
    await settings_button_handler(callback.message)
    await callback.answer()