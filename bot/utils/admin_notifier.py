"""
Утиліта для сповіщення адміністраторів про події в системі.
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Імпорт з config.py
try:
    from config import ADMIN_TELEGRAM_IDS
except ImportError:
    # Fallback якщо запускається окремо
    ADMIN_TELEGRAM_IDS = []

logger = logging.getLogger(__name__)


async def notify_admin_new_address(
        bot: Bot,
        user_id: int,
        username: Optional[str],
        first_name: str,
        street: str,
        house: str,
        queue_id: int
) -> None:
    """
    Надіслати уведомлення адмінам про новий адрес від користувача.

    Args:
        bot: Екземпляр Telegram бота
        user_id: Telegram ID користувача
        username: Username користувача (може бути None)
        first_name: Ім'я користувача
        street: Назва вулиці
        house: Номер будинку
        queue_id: ID черги світла
    """

    # Формуємо username для показу
    username_display = f"@{username}" if username else "немає username"

    # Формуємо повідомлення
    message = (
        f"📍 <b>НОВИЙ АДРЕС</b>\n\n"
        f"👤 Користувач: {first_name} ({username_display})\n"
        f"🆔 ID: <code>{user_id}</code>\n\n"
        f"🏠 Адреса: {street}, {house}\n"
        f"🔢 Черга: {queue_id}\n\n"
        f"Додати цю адресу до бази?"
    )

    # Створюємо клавіатуру з кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Підтвердити",
                callback_data=f"admin_approve_address_{user_id}_{queue_id}_{street}_{house}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Відхилити",
                callback_data=f"admin_reject_address_{user_id}"
            )
        ]
    ])

    # Відправляємо всім адмінам
    sent_count = 0
    for admin_id in ADMIN_TELEGRAM_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            sent_count += 1
            logger.info(f"✅ Admin notification sent to {admin_id}")

        except Exception as e:
            logger.error(f"❌ Failed to notify admin {admin_id}: {e}")

    logger.info(
        f"Admin notifications sent: {sent_count}/{len(ADMIN_TELEGRAM_IDS)} "
        f"for new address: {street}, {house}"
    )


async def notify_admin_verification_needed(
        bot: Bot,
        user_id: int,
        username: Optional[str],
        first_name: str,
        reason: str
) -> None:
    """
    Надіслати уведомлення адмінам про потребу в перевірці користувача.

    Args:
        bot: Екземпляр Telegram бота
        user_id: Telegram ID користувача
        username: Username користувача
        first_name: Ім'я користувача
        reason: Причина потреби в перевірці
    """

    username_display = f"@{username}" if username else "немає username"

    message = (
        f"⚠️ <b>ПОТРІБНА ПЕРЕВІРКА</b>\n\n"
        f"👤 Користувач: {first_name} ({username_display})\n"
        f"🆔 ID: <code>{user_id}</code>\n\n"
        f"📝 Причина: {reason}"
    )

    for admin_id in ADMIN_TELEGRAM_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"❌ Failed to notify admin {admin_id}: {e}")


async def notify_admin_spam_detected(
        bot: Bot,
        user_id: int,
        username: Optional[str],
        action: str,
        count: int
) -> None:
    """
    Надіслати уведомлення адмінам про підозру на спам.

    Args:
        bot: Екземпляр Telegram бота
        user_id: Telegram ID користувача
        username: Username користувача
        action: Дія, яку виконав користувач
        count: Кількість разів за короткий час
    """

    username_display = f"@{username}" if username else "немає username"

    message = (
        f"🚨 <b>ПІДОЗРА НА СПАМ</b>\n\n"
        f"👤 Користувач: {username_display}\n"
        f"🆔 ID: <code>{user_id}</code>\n\n"
        f"📊 Дія: {action}\n"
        f"🔢 Кількість: {count} разів\n\n"
        f"Можливо потрібно заблокувати користувача."
    )

    for admin_id in ADMIN_TELEGRAM_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"❌ Failed to notify admin {admin_id}: {e}")