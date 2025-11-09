"""
Обробники callback-кнопок для адміністраторів.
Тільки користувачі з ID в ADMIN_TELEGRAM_IDS можуть використовувати ці команди.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter

# Імпорти
from config import ADMIN_TELEGRAM_IDS
# API клієнт буде встановлено через set_api_client()
# Імпорт не потрібен!

logger = logging.getLogger(__name__)
router = Router()

# Ініціалізація API клієнта (буде створений при старті бота)
api_client = None


def set_api_client(client):
    """Встановити API клієнт (викликається при старті бота)"""
    global api_client
    api_client = client


def is_admin(user_id: int) -> bool:
    """Перевірити чи є користувач адміністратором"""
    return user_id in ADMIN_TELEGRAM_IDS


@router.callback_query(F.data.startswith("admin_approve_address_"))
async def approve_address(callback: CallbackQuery):
    """
    Підтвердити новий адрес і додати його до бази даних.
    """
    # Перевірка прав адміністратора
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас немає прав адміністратора!", show_alert=True)
        return

    try:
        # Парсинг callback_data
        parts = callback.data.split("_")
        user_id = int(parts[3])
        queue_id = int(parts[4])
        street = "_".join(parts[5:-1])
        house = parts[-1]

        logger.info(
            f"Admin {callback.from_user.id} approving address: "
            f"user={user_id}, queue={queue_id}, street={street}, house={house}"
        )

        # Створюємо адрес в базі даних
        if api_client is None:
            await callback.answer("❌ API client not initialized", show_alert=True)
            return

        address_data = {
            "street": street,
            "house_number": house,
            "queue_id": queue_id,
            "verified": True
        }

        # Створюємо адрес
        new_address = await api_client.post("/api/addresses/", address_data)

        if not new_address or "id" not in new_address:
            await callback.answer("❌ Помилка при створенні адреси", show_alert=True)
            return

        address_id = new_address["id"]

        # Оновлюємо primary_address_id користувача
        await api_client.patch(
            f"/api/users/{user_id}",
            {"primary_address_id": address_id}
        )

        # Відповідь адміну
        success_message = (
            f"✅ <b>АДРЕСУ ПІДТВЕРДЖЕНО</b>\n\n"
            f"🏠 {street}, {house}\n"
            f"🔢 Черга: {queue_id}\n"
            f"👤 Користувач ID: {user_id}\n"
            f"🆔 Address ID: {address_id}"
        )

        await callback.message.edit_text(
            callback.message.text + "\n\n" + success_message,
            parse_mode="HTML"
        )

        await callback.answer("✅ Адресу підтверджено!", show_alert=False)

        logger.info(f"✅ Address approved: {address_id}")

    except Exception as e:
        logger.error(f"❌ Error approving address: {e}", exc_info=True)
        await callback.answer("❌ Помилка при підтвердженні", show_alert=True)


@router.callback_query(F.data.startswith("admin_reject_address_"))
async def reject_address(callback: CallbackQuery):
    """
    Відхилити новий адрес.

    Callback data format: admin_reject_address_{user_id}
    """

    # Перевірка прав адміністратора
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас немає прав адміністратора!", show_alert=True)
        return

    try:
        # Парсинг callback_data
        parts = callback.data.split("_")
        user_id = int(parts[3])

        logger.info(f"Admin {callback.from_user.id} rejecting address for user {user_id}")

        # Оновлюємо повідомлення
        reject_message = (
            f"\n\n❌ <b>АДРЕСУ ВІДХИЛЕНО</b>\n"
            f"Адміністратор: @{callback.from_user.username or callback.from_user.first_name}"
        )

        await callback.message.edit_text(
            callback.message.text + reject_message,
            parse_mode="HTML"
        )

        await callback.answer("❌ Адресу відхилено", show_alert=False)

        logger.info(f"✅ Address rejected for user {user_id}")

        # TODO: Відправити користувачу повідомлення про відхилення
        # await callback.bot.send_message(
        #     user_id,
        #     "❌ На жаль, ваш адрес не підтверджено адміністратором.\n"
        #     "Спробуйте ввести адресу ще раз або оберіть чергу вручну."
        # )

    except Exception as e:
        logger.error(f"❌ Error rejecting address: {e}", exc_info=True)
        await callback.answer("❌ Помилка при відхиленні адреси", show_alert=True)


@router.callback_query(F.data.startswith("admin_ban_user_"))
async def ban_user(callback: CallbackQuery):
    """
    Заблокувати користувача (для боротьби зі спамом).

    Callback data format: admin_ban_user_{user_id}
    """

    # Перевірка прав адміністратора
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас немає прав адміністратора!", show_alert=True)
        return

    try:
        # Парсинг callback_data
        parts = callback.data.split("_")
        user_id = int(parts[3])

        logger.info(f"Admin {callback.from_user.id} banning user {user_id}")

        if api_client is None:
            await callback.answer("❌ API client not initialized", show_alert=True)
            return

        # Оновлюємо статус користувача
        await api_client.patch(
            f"/api/users/{user_id}",
            {"is_banned": True}
        )

        # Оновлюємо повідомлення
        ban_message = (
            f"\n\n🚫 <b>КОРИСТУВАЧА ЗАБЛОКОВАНО</b>\n"
            f"Адміністратор: @{callback.from_user.username or callback.from_user.first_name}"
        )

        await callback.message.edit_text(
            callback.message.text + ban_message,
            parse_mode="HTML"
        )

        await callback.answer("🚫 Користувача заблоковано", show_alert=False)

        logger.info(f"✅ User {user_id} banned")

    except Exception as e:
        logger.error(f"❌ Error banning user: {e}", exc_info=True)
        await callback.answer("❌ Помилка при блокуванні користувача", show_alert=True)


# Експорт роутера
__all__ = ["router", "set_api_client"]