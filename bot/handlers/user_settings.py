from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging

from api_client import api_client
from keyboards.reply import get_main_keyboard
from keyboards.inline import get_info_keyboard
from states import SettingsStates

logger = logging.getLogger(__name__)
router = Router()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для меню налаштувань
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мої адреси", callback_data="settings_addresses")],
        [InlineKeyboardButton(text="🔔 Сповіщення", callback_data="settings_notifications")],
        [InlineKeyboardButton(text="💳 Підписка", callback_data="settings_subscription")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    return keyboard


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


@router.callback_query(F.data == "settings_addresses")
async def settings_addresses(callback: CallbackQuery):
    """Управление адресами"""
    await callback.message.edit_text(
        "<b>📋 Мої адреси</b>\n\n"
        "🔜 Функція в розробці\n\n"
        "Тут ви зможете:\n"
        "• Переглядати свої адреси\n"
        "• Додавати нові адреси\n"
        "• Змінювати основну адресу",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "settings_notifications")
async def settings_notifications(callback: CallbackQuery):
    """Настройки уведомлений"""
    await callback.message.edit_text(
        "<b>🔔 Налаштування сповіщень</b>\n\n"
        "🔜 Функція в розробці\n\n"
        "Тут ви зможете:\n"
        "• Увімкнути/вимкнути сповіщення\n"
        "• Налаштувати тихі сповіщення\n"
        "• Вибрати час сповіщень",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "settings_subscription")
async def settings_subscription(callback: CallbackQuery):
    """Информация о подписке"""
    user_id = callback.from_user.id

    try:
        user = await api_client.get_user(user_id)

        tier = user.get('subscription_tier', 'FREE')
        expires = user.get('subscription_expires_at', 'Немає')

        await callback.message.edit_text(
            "<b>💳 Моя підписка</b>\n\n"
            f"📋 Тариф: {tier}\n"
            f"📅 Діє до: {expires}\n\n"
            "🔜 Управління підпискою в розробці",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")]
            ])
        )
    except Exception as e:
        logger.error(f"Error loading subscription for {user_id}: {e}")
        await callback.message.edit_text(
            "❌ Помилка завантаження інформації про підписку",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")]
            ])
        )

    await callback.answer()