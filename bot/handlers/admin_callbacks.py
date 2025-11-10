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


@router.callback_query(F.data.startswith("appr_"))
async def approve_address(callback: CallbackQuery):
    """
    Підтвердити новий адрес і додати його до бази даних.

    Callback data format: appr_{user_id}_{queue_id}
    ВАЖЛИВО: Адрес вже створений в start.py, тут тільки підтверджуємо!
    """
    # Перевірка прав адміністратора
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас немає прав адміністратора!", show_alert=True)
        return

    try:
        # Парсинг callback_data: appr_{user_id}_{queue_id}
        parts = callback.data.split("_")
        user_id = int(parts[1])
        queue_id = int(parts[2])

        logger.info(
            f"Admin {callback.from_user.id} approving address for "
            f"user={user_id}, queue={queue_id}"
        )

        if api_client is None:
            await callback.answer("❌ API client not initialized", show_alert=True)
            return

        # Получаем информацию о пользователе
        user = await api_client.get(f"/api/users/{user_id}")

        if not user or not user.get("primary_address_id"):
            await callback.answer("❌ Адрес не знайдено у користувача", show_alert=True)
            return

        address_id = user["primary_address_id"]

        # Получаем информацию об адресе
        address = await api_client.get(f"/api/addresses/{address_id}")

        if not address:
            await callback.answer("❌ Адрес не знайдено в БД", show_alert=True)
            return

        await api_client.patch(
            f"/api/addresses/{address_id}",
            {"added_by": "admin"}
        )

        # Відповідь адміну
        success_message = (
            f"\n\n✅ <b>АДРЕСУ ПІДТВЕРДЖЕНО</b>\n"
            f"🏠 {address['street']}, {address['house_number']}\n"
            f"🔢 Черга: {address['queue_id']}\n"
            f"👤 Користувач ID: {user_id}\n"
            f"🆔 Address ID: {address_id}\n"
            f"👨‍💼 Адмін: @{callback.from_user.username or callback.from_user.first_name}"
        )

        await callback.message.edit_text(
            callback.message.text + success_message,
            parse_mode="HTML"
        )

        await callback.answer("✅ Адресу підтверджено!", show_alert=False)

        logger.info(f"✅ Address {address_id} approved by admin {callback.from_user.id}")

        # TODO: Відправити користувачу повідомлення про підтвердження
        # await callback.bot.send_message(
        #     user_id,
        #     f"✅ Ваш адрес підтверджено адміністратором!\n"
        #     f"📍 {address['street']}, {address['house_number']}\n"
        #     f"🔢 Черга: {address['queue_id']}"
        # )

    except Exception as e:
        logger.error(f"❌ Error approving address: {e}", exc_info=True)
        await callback.answer("❌ Помилка при підтвердженні", show_alert=True)


@router.callback_query(F.data.startswith("rejct_"))
async def reject_address(callback: CallbackQuery):
    """
    Відхилити новий адрес.

    Callback data format: rejct_{user_id}
    """

    # Перевірка прав адміністратора
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас немає прав адміністратора!", show_alert=True)
        return

    try:
        # Парсинг callback_data: rejct_{user_id}
        parts = callback.data.split("_")
        user_id = int(parts[1])

        logger.info(f"Admin {callback.from_user.id} rejecting address for user {user_id}")

        if api_client is None:
            await callback.answer("❌ API client not initialized", show_alert=True)
            return

        # Получаем информацию о пользователе
        user = await api_client.get(f"/api/users/{user_id}")

        if user and user.get("primary_address_id"):
            address_id = user["primary_address_id"]

            # Помечаем адрес как неподтверждённый
            await api_client.patch(
                f"/api/addresses/{address_id}",
                {"verified": False}
            )

            # Убираем адрес у пользователя
            await api_client.patch(
                f"/api/users/{user_id}",
                {"primary_address_id": None}
            )

        # Оновлюємо повідомлення
        reject_message = (
            f"\n\n❌ <b>АДРЕСУ ВІДХИЛЕНО</b>\n"
            f"👨‍💼 Адмін: @{callback.from_user.username or callback.from_user.first_name}"
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