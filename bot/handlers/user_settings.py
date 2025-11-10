"""
Обробники для розділу Налаштування
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from api_client import api_client
from keyboards.reply import get_main_keyboard, get_address_method_keyboard
from states import RegistrationStates

logger = logging.getLogger(__name__)
router = Router()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Головне меню налаштувань (5 кнопок)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Мої адреси", callback_data="settings_addresses")],
        [InlineKeyboardButton(text="🔔 Сповіщення", callback_data="settings_notifications")],
        [InlineKeyboardButton(text="💳 Підписка", callback_data="settings_subscription")],
        [InlineKeyboardButton(text="👥 Реферальна програма", callback_data="settings_referral")],
        [InlineKeyboardButton(text="🗑️ Видалення акаунту", callback_data="settings_delete")]
    ])
    return keyboard


def get_back_to_settings_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад до налаштувань"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back")]
    ])


# ========== ГОЛОВНЕ МЕНЮ НАЛАШТУВАНЬ ==========
@router.message(F.text == "⚙️ Налаштування")
async def settings_menu(message: Message):
    """Головне меню налаштувань"""
    user_id = message.from_user.id

    try:
        user = await api_client.get(f"/api/users/{user_id}")

        tier = user.get('subscription_tier', 'FREE')
        expires = user.get('subscription_expires_at')

        # Форматування дати
        if expires:
            try:
                expires_dt = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                expires_str = expires_dt.strftime('%d.%m.%Y')
            except:
                expires_str = "Невідомо"
        else:
            expires_str = "Безстроково" if tier in ['FREE', 'NOFREE'] else "Невідомо"

        await message.answer(
            "⚙️ <b>НАЛАШТУВАННЯ</b>\n\n"
            f"👤 Користувач: {message.from_user.first_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📋 Тариф: {tier}\n"
            f"📅 Діє до: {expires_str}\n\n"
            "Оберіть розділ:",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading settings for {user_id}: {e}")
        await message.answer(
            "⚙️ <b>НАЛАШТУВАННЯ</b>\n\n"
            "Оберіть розділ:",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "settings_back")
async def settings_back(callback: CallbackQuery):
    """Повернення до головного меню налаштувань"""
    user_id = callback.from_user.id

    try:
        user = await api_client.get(f"/api/users/{user_id}")

        tier = user.get('subscription_tier', 'FREE')
        expires = user.get('subscription_expires_at')

        if expires:
            try:
                expires_dt = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                expires_str = expires_dt.strftime('%d.%m.%Y')
            except:
                expires_str = "Невідомо"
        else:
            expires_str = "Безстроково" if tier in ['FREE', 'NOFREE'] else "Невідомо"

        await callback.message.edit_text(
            "⚙️ <b>НАЛАШТУВАННЯ</b>\n\n"
            f"👤 Користувач: {callback.from_user.first_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📋 Тариф: {tier}\n"
            f"📅 Діє до: {expires_str}\n\n"
            "Оберіть розділ:",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in settings_back: {e}")
        await callback.message.edit_text(
            "⚙️ <b>НАЛАШТУВАННЯ</b>\n\n"
            "Оберіть розділ:",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML"
        )

    await callback.answer()


# ========== 1. МОЇ АДРЕСИ ==========
@router.callback_query(F.data == "settings_addresses")
async def settings_addresses(callback: CallbackQuery):
    """Управління адресами"""
    user_id = callback.from_user.id

    try:
        user = await api_client.get(f"/api/users/{user_id}")
        tier = user.get('subscription_tier', 'FREE')

        # Отримати всі адреси користувача
        addresses = await api_client.get(f"/api/users/{user_id}/addresses")

        if not addresses:
            addresses = []

        addresses_count = len(addresses)
        max_addresses = 3 if tier == 'PRO' else 1

        # Формування тексту
        text = "📍 <b>МОЇ АДРЕСИ</b>\n\n"

        if addresses_count == 0:
            text += "❌ У вас немає жодної адреси.\n\n"
        else:
            text += "Ви отримуєте сповіщення для ВСІХ адрес:\n\n"

            for idx, addr in enumerate(addresses, 1):
                emoji = "1️⃣2️⃣3️⃣"[idx - 1] if idx <= 3 else f"{idx}."
                text += (
                    f"{emoji} {addr['street']}, {addr['house_number']}\n"
                    f"   🔢 Черга: {addr['queue_id']}\n\n"
                )

        # Формування кнопок
        keyboard = []

        # Кнопки для кожної адреси (якщо > 1)
        if addresses_count > 1:
            for idx, addr in enumerate(addresses, 1):
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"✏️ Змінити #{idx}",
                        callback_data=f"addr_edit_{addr['id']}"
                    ),
                    InlineKeyboardButton(
                        text=f"🗑️ Видалити #{idx}",
                        callback_data=f"addr_del_{addr['id']}"
                    )
                ])
        elif addresses_count == 1:
            keyboard.append([
                InlineKeyboardButton(
                    text="✏️ Змінити адресу",
                    callback_data=f"addr_edit_{addresses[0]['id']}"
                )
            ])

        # Кнопка додати адресу
        if tier == 'PRO' and addresses_count < 3:
            keyboard.append([
                InlineKeyboardButton(
                    text="➕ Додати адресу",
                    callback_data="addr_add"
                )
            ])
            text += f"💎 PRO: {addresses_count}/3 адрес\n"
        elif tier != 'PRO' and addresses_count < max_addresses:
            keyboard.append([
                InlineKeyboardButton(
                    text="➕ Додати адресу",
                    callback_data="addr_add"
                )
            ])
        elif tier != 'PRO':
            text += "\n🔒 Додаткові адреси доступні в PRO\n"
            text += "👑 Оформіть PRO для моніторингу до 3 адрес\n"

        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in settings_addresses: {e}")
        await callback.message.edit_text(
            "❌ Помилка завантаження адрес",
            reply_markup=get_back_to_settings_keyboard()
        )

    await callback.answer()


@router.callback_query(F.data.startswith("addr_edit_"))
async def edit_address(callback: CallbackQuery, state: FSMContext):
    """Редагування адреси"""
    # TODO: Реалізувати зміну адреси (запустити процес реєстрації)
    await callback.answer("🔜 Функція в розробці", show_alert=True)


@router.callback_query(F.data.startswith("addr_del_"))
async def delete_address(callback: CallbackQuery):
    """Видалення адреси"""
    address_id = int(callback.data.split("_")[2])

    # Підтвердження видалення
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"addr_del_confirm_{address_id}"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="settings_addresses")
        ]
    ])

    await callback.message.edit_text(
        "⚠️ <b>Видалення адреси</b>\n\n"
        "Ви впевнені, що хочете видалити цю адресу?\n"
        "Ви перестанете отримувати сповіщення для неї.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("addr_del_confirm_"))
async def delete_address_confirm(callback: CallbackQuery):
    """Підтвердження видалення адреси"""
    address_id = int(callback.data.split("_")[3])

    try:
        await api_client.delete(f"/api/addresses/{address_id}")
        await callback.answer("✅ Адресу видалено", show_alert=True)

        # Повернутись до списку адрес
        await settings_addresses(callback)

    except Exception as e:
        logger.error(f"Error deleting address: {e}")
        await callback.answer("❌ Помилка видалення адреси", show_alert=True)


@router.callback_query(F.data == "addr_add")
async def add_address(callback: CallbackQuery, state: FSMContext):
    """Додавання нової адреси"""
    # TODO: Запустити процес додавання адреси
    await callback.answer("🔜 Функція в розробці", show_alert=True)


# ========== 2. СПОВІЩЕННЯ ==========
@router.callback_query(F.data == "settings_notifications")
async def settings_notifications(callback: CallbackQuery):
    """Налаштування сповіщень"""
    user_id = callback.from_user.id

    try:
        user = await api_client.get(f"/api/users/{user_id}")
        tier = user.get('subscription_tier', 'FREE')

        # Поточні налаштування
        notif_before_off = user.get('notification_before_off', 15)
        notif_before_on = user.get('notification_before_on', 15)
        quiet_mode = user.get('quiet_mode_enabled', False)
        critical_notif = user.get('critical_notifications_enabled', True)

        text = "🔔 <b>НАЛАШТУВАННЯ СПОВІЩЕНЬ</b>\n\n"

        # Тихий режим
        if quiet_mode:
            text += "🌙 <b>Тихий режим:</b> УВІМКНЕНО ✅\n"
            text += "   Без сповіщень: 23:00-07:00\n\n"
        else:
            text += "🔔 <b>Тихий режим:</b> ВИМКНЕНО\n"
            text += "   Сповіщення приходять 24/7\n\n"

        # Інтервали попереджень
        if tier in ['STANDARD', 'TRIAL', 'PRO']:
            text += f"⏰ <b>Попередження ПЕРЕД відключенням:</b>\n"
            text += f"   {notif_before_off} хвилин\n\n"

            text += f"⏰ <b>Попередження ПЕРЕД включенням:</b>\n"
            text += f"   {notif_before_on} хвилин\n\n"

            if notif_before_off == 0 and notif_before_on == 0:
                text += "💡 Попередження вимкнені\n"
                text += "   Тільки фактичні ON/OFF\n\n"

        # Критичні сповіщення
        if tier == 'PRO':
            if critical_notif:
                text += "🚨 <b>Критичні інсайдерські сповіщення:</b>\n"
                text += "   УВІМКНЕНО ✅\n\n"
            else:
                text += "🔕 <b>Критичні інсайдерські сповіщення:</b>\n"
                text += "   ВИМКНЕНО\n\n"

        # Формування кнопок
        keyboard = []

        # Тихий режим
        if quiet_mode:
            keyboard.append([InlineKeyboardButton(
                text="🔔 Вимкнути тихий режим",
                callback_data="notif_quiet_off"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                text="🌙 Увімкнути тихий режим",
                callback_data="notif_quiet_on"
            )])

        # Інтервали (тільки для STANDARD+)
        if tier in ['STANDARD', 'TRIAL', 'PRO']:
            keyboard.append([InlineKeyboardButton(
                text="⏰ Змінити попередження ПЕРЕД відключенням",
                callback_data="notif_interval_off"
            )])
            keyboard.append([InlineKeyboardButton(
                text="⏰ Змінити попередження ПЕРЕД включенням",
                callback_data="notif_interval_on"
            )])

        # Критичні сповіщення
        if tier == 'PRO':
            if critical_notif:
                keyboard.append([InlineKeyboardButton(
                    text="🔕 Вимкнути критичні сповіщення",
                    callback_data="notif_critical_off"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    text="🚨 Увімкнути критичні сповіщення",
                    callback_data="notif_critical_on"
                )])
        elif tier in ['STANDARD', 'TRIAL']:
            keyboard.append([InlineKeyboardButton(
                text="🚨 Критичні сповіщення (тільки PRO)",
                callback_data="notif_critical_promo"
            )])

        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in settings_notifications: {e}")
        await callback.message.edit_text(
            "❌ Помилка завантаження налаштувань",
            reply_markup=get_back_to_settings_keyboard()
        )

    await callback.answer()


# Обробники для сповіщень
@router.callback_query(F.data == "notif_quiet_on")
async def enable_quiet_mode(callback: CallbackQuery):
    """Увімкнути тихий режим"""
    try:
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {"quiet_mode_enabled": True}
        )
        await callback.answer("🌙 Тихий режим увімкнено", show_alert=True)
        await settings_notifications(callback)
    except Exception as e:
        logger.error(f"Error enabling quiet mode: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data == "notif_quiet_off")
async def disable_quiet_mode(callback: CallbackQuery):
    """Вимкнути тихий режим"""
    try:
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {"quiet_mode_enabled": False}
        )
        await callback.answer("🔔 Тихий режим вимкнено", show_alert=True)
        await settings_notifications(callback)
    except Exception as e:
        logger.error(f"Error disabling quiet mode: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data == "notif_interval_off")
async def change_interval_off(callback: CallbackQuery):
    """Змінити інтервал попередження ПЕРЕД відключенням"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0 хв", callback_data="interval_off_0"),
            InlineKeyboardButton(text="5 хв", callback_data="interval_off_5"),
            InlineKeyboardButton(text="10 хв", callback_data="interval_off_10")
        ],
        [
            InlineKeyboardButton(text="15 хв", callback_data="interval_off_15"),
            InlineKeyboardButton(text="30 хв", callback_data="interval_off_30"),
            InlineKeyboardButton(text="60 хв", callback_data="interval_off_60")
        ],
        [
            InlineKeyboardButton(text="120 хв", callback_data="interval_off_120")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_notifications")]
    ])

    await callback.message.edit_text(
        "⏰ <b>Попередження ПЕРЕД відключенням</b>\n\n"
        "Оберіть за скільки хвилин ви хочете отримувати попередження:\n\n"
        "• 0 хв = тільки фактичні ON/OFF\n"
        "• 15 хв = рекомендовано",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("interval_off_"))
async def set_interval_off(callback: CallbackQuery):
    """Встановити інтервал попередження перед відключенням"""
    minutes = int(callback.data.split("_")[2])

    try:
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {"notification_before_off": minutes}
        )
        await callback.answer(f"✅ Встановлено {minutes} хв", show_alert=True)
        await settings_notifications(callback)
    except Exception as e:
        logger.error(f"Error setting interval: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data == "notif_interval_on")
async def change_interval_on(callback: CallbackQuery):
    """Змінити інтервал попередження ПЕРЕД включенням"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0 хв", callback_data="interval_on_0"),
            InlineKeyboardButton(text="5 хв", callback_data="interval_on_5"),
            InlineKeyboardButton(text="10 хв", callback_data="interval_on_10")
        ],
        [
            InlineKeyboardButton(text="15 хв", callback_data="interval_on_15"),
            InlineKeyboardButton(text="30 хв", callback_data="interval_on_30"),
            InlineKeyboardButton(text="60 хв", callback_data="interval_on_60")
        ],
        [
            InlineKeyboardButton(text="120 хв", callback_data="interval_on_120")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_notifications")]
    ])

    await callback.message.edit_text(
        "⏰ <b>Попередження ПЕРЕД включенням</b>\n\n"
        "Оберіть за скільки хвилин ви хочете отримувати попередження:\n\n"
        "• 0 хв = тільки фактичні ON/OFF\n"
        "• 15 хв = рекомендовано",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("interval_on_"))
async def set_interval_on(callback: CallbackQuery):
    """Встановити інтервал попередження перед включенням"""
    minutes = int(callback.data.split("_")[2])

    try:
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {"notification_before_on": minutes}
        )
        await callback.answer(f"✅ Встановлено {minutes} хв", show_alert=True)
        await settings_notifications(callback)
    except Exception as e:
        logger.error(f"Error setting interval: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data == "notif_critical_on")
async def enable_critical(callback: CallbackQuery):
    """Увімкнути критичні сповіщення"""
    try:
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {"critical_notifications_enabled": True}
        )
        await callback.answer("🚨 Критичні сповіщення увімкнено", show_alert=True)
        await settings_notifications(callback)
    except Exception as e:
        logger.error(f"Error enabling critical: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data == "notif_critical_off")
async def disable_critical(callback: CallbackQuery):
    """Вимкнути критичні сповіщення"""
    try:
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {"critical_notifications_enabled": False}
        )
        await callback.answer("🔕 Критичні сповіщення вимкнено", show_alert=True)
        await settings_notifications(callback)
    except Exception as e:
        logger.error(f"Error disabling critical: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data == "notif_critical_promo")
async def critical_promo(callback: CallbackQuery):
    """Реклама критичних сповіщень для STANDARD"""
    await callback.message.edit_text(
        "🚨 <b>КРИТИЧНІ ІНСАЙДЕРСЬКІ СПОВІЩЕННЯ</b>\n\n"
        "🔒 <b>Доступно тільки в PRO</b>\n\n"
        "Отримуйте інсайдерську інформацію про:\n"
        "• Критичні аварії на підстанціях\n"
        "• Незаплановані відключення\n"
        "• Терміновіінформаційні повідомлення\n\n"
        "💎 <b>Оформіть PRO:</b> до 10 грн/міс",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Оформити PRO", callback_data="settings_subscription")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_notifications")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== 3. ПІДПИСКА ==========
@router.callback_query(F.data == "settings_subscription")
async def settings_subscription(callback: CallbackQuery):
    """Управління підпискою з детальним описом тарифів"""
    user_id = callback.from_user.id

    try:
        user = await api_client.get(f"/api/users/{user_id}")

        tier = user.get('subscription_tier', 'FREE')
        expires = user.get('subscription_expires_at')

        text = "💳 <b>МОЯ ПІДПИСКА</b>\n\n"
        text += f"📋 Поточний тариф: <b>{tier}</b>\n"

        # Дата закінчення
        if expires:
            try:
                expires_dt = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                expires_str = expires_dt.strftime('%d.%m.%Y')

                # Залишилось днів
                days_left = (expires_dt - datetime.now()).days
                if days_left > 0:
                    text += f"📅 Діє до: {expires_str}\n"
                    text += f"⏰ Залишилось: {days_left} днів\n\n"
                else:
                    text += f"⚠️ Підписка закінчилась {expires_str}\n\n"
            except:
                text += "📅 Діє до: Невідомо\n\n"
        else:
            text += "📅 Діє до: Безстроково\n\n"

        # Детальний опис всіх тарифів
        text += "─────────────────────\n"
        text += "📋 <b>ТАРИФНІ ПЛАНИ</b>\n\n"

        # FREE
        if tier == 'FREE':
            text += "✅ <b>FREE (ваш тариф)</b>\n"
        else:
            text += "📋 <b>FREE</b>\n"
        text += "• 1 адреса\n"
        text += "• Базові сповіщення ON/OFF\n"
        text += "• Тихий режим (23:00-07:00)\n\n"

        # STANDARD
        if tier in ['STANDARD', 'TRIAL']:
            text += "✅ <b>STANDARD (ваш тариф)</b>\n"
        else:
            text += "⭐ <b>STANDARD</b>\n"
        text += "• 1 адреса\n"
        text += "• Налаштування періодів попереджень\n"
        text += "• Все з FREE\n"
        text += "🎁 <b>Як отримати?</b> Запросіть друзів!\n"
        text += "   +5 днів за кожного реферала\n\n"

        # PRO
        if tier == 'PRO':
            text += "✅ <b>PRO (ваш тариф)</b>\n"
        else:
            text += "💎 <b>PRO</b>\n"
        text += "• До 3 адрес одночасно\n"
        text += "• Критичні інсайдерські сповіщення\n"
        text += "• Все з STANDARD\n"
        text += "💰 <b>Вартість:</b> до 10 грн/міс\n\n"

        text += "─────────────────────\n"
        text += "💡 <b>Всі сповіщення містять ваше реф-посилання!</b>\n"
        text += "Репостніть їх в групи та отримуйте\n"
        text += "нових рефералів автоматично!\n\n"

        # Кнопки
        keyboard = []

        # Кнопка "Як отримати STANDARD" для FREE користувачів
        if tier == 'FREE':
            keyboard.append([InlineKeyboardButton(
                text="🎁 Як отримати STANDARD безкоштовно?",
                callback_data="how_to_get_standard"
            )])

        if tier != 'PRO':
            keyboard.append([InlineKeyboardButton(
                text="👑 Оформити PRO (до 10 грн/міс)",
                callback_data="buy_pro"
            )])

        keyboard.append([InlineKeyboardButton(
            text="👥 Реферальна програма",
            callback_data="settings_referral"
        )])

        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in settings_subscription: {e}")
        await callback.message.edit_text(
            "❌ Помилка завантаження підписки",
            reply_markup=get_back_to_settings_keyboard()
        )

    await callback.answer()


@router.callback_query(F.data == "how_to_get_standard")
async def how_to_get_standard(callback: CallbackQuery):
    """Інформація як отримати STANDARD безкоштовно"""
    user_id = callback.from_user.id

    try:
        user = await api_client.get(f"/api/users/{user_id}")
        ref_link = f"https://t.me/svitlobot?start={user_id}"

        text = (
            "🎁 <b>ЯК ОТРИМАТИ STANDARD БЕЗКОШТОВНО?</b>\n\n"
            "⭐ Запросіть друзів через своє реферальне посилання!\n\n"
            f"🔗 <b>Ваше посилання:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            "🎯 <b>Умови:</b>\n"
            "• За кожного реферала: <b>+5 днів</b> STANDARD\n"
            "• Реферал має зареєструватись у боті\n"
            "• Бонуси сумуються!\n\n"
            "💡 <b>Приклад:</b>\n"
            "• 6 рефералів = 30 днів (1 місяць)\n"
            "• 12 рефералів = 60 днів (2 місяці)\n"
            "• 36 рефералів = 180 днів (6 місяців)\n\n"
            "📤 <b>Як поширювати?</b>\n"
            "• Відправте друзям в Telegram\n"
            "• Поділіться в групах\n"
            "• Репостніть сповіщення (вони містять ваше посилання!)\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📤 Поділитися посиланням",
                switch_inline_query=f"Приєднуйся до СвітлоБот! Код: {user_id}"
            )],
            [InlineKeyboardButton(
                text="👥 Моя реферальна програма",
                callback_data="settings_referral"
            )],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_subscription")]
        ])

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error in how_to_get_standard: {e}")
        await callback.answer("❌ Помилка", show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "buy_pro")
async def buy_pro(callback: CallbackQuery):
    """Купівля PRO підписки"""
    await callback.answer("🔜 Оплата в розробці (Крок 7)", show_alert=True)


# ========== 4. РЕФЕРАЛЬНА ПРОГРАМА ==========
# (Продовжую в наступній частині файлу через обмеження розміру)

@router.callback_query(F.data == "settings_referral")
async def settings_referral(callback: CallbackQuery):
    """Реферальна програма"""
    user_id = callback.from_user.id

    try:
        user = await api_client.get(f"/api/users/{user_id}")

        # Статистика
        stats = await api_client.get(f"/api/users/{user_id}/referral-stats")

        total_refs = stats.get('total_referrals', 0)
        active_refs = stats.get('active_referrals', 0)
        bonus_days = stats.get('bonus_days', 0)
        rank = stats.get('rank', 0)
        total_users = stats.get('total_users', 1)

        # Реферальне посилання (ID користувача)
        ref_link = f"https://t.me/svitlobot?start={user_id}"

        text = "👥 <b>РЕФЕРАЛЬНА ПРОГРАМА</b>\n\n"
        text += f"🔗 Ваше реф-посилання:\n"
        text += f"<code>{ref_link}</code>\n\n"
        text += f"📊 <b>Статистика:</b>\n"
        text += f"• Запрошено друзів: {total_refs}\n"
        text += f"• Активних: {active_refs}\n"
        text += f"• Отримано: +{bonus_days} днів STANDARD\n\n"

        if rank > 0:
            text += f"🏆 Ваш рейтинг: #{rank} (з {total_users:,})\n"

            if rank <= 10:
                text += "🥇 Топ-10 учасників!\n\n"
            elif rank <= 100:
                text += "🏅 Топ-100 учасників!\n\n"
            else:
                text += "\n"

        # Кнопки
        keyboard = [
            [InlineKeyboardButton(
                text="📤 Поділитися посиланням",
                switch_inline_query=f"Приєднуйся до СвітлоБот! Код: {user_id}"
            )],
            [InlineKeyboardButton(
                text="🏆 Переглянути рейтинг (топ-10)",
                callback_data="ref_leaderboard"
            )],
            [InlineKeyboardButton(
                text="📋 Список моїх рефералів",
                callback_data="ref_list_0"
            )]
        ]

        # Кнопка вимкнення сповіщень
        ref_notif_enabled = user.get('referral_notifications_enabled', True)
        if ref_notif_enabled:
            keyboard.append([InlineKeyboardButton(
                text="🔕 Вимкнути сповіщення про рефералів",
                callback_data="ref_notif_off"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                text="🔔 Увімкнути сповіщення про рефералів",
                callback_data="ref_notif_on"
            )])

        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error in settings_referral: {e}")
        await callback.message.edit_text(
            "❌ Помилка завантаження реферальної програми",
            reply_markup=get_back_to_settings_keyboard()
        )

    await callback.answer()


@router.callback_query(F.data == "ref_leaderboard")
async def referral_leaderboard(callback: CallbackQuery):
    """Рейтинг топ-10"""
    try:
        leaderboard = await api_client.get("/api/users/referral-leaderboard?limit=10")

        user_id = callback.from_user.id

        text = "🏆 <b>РЕЙТИНГ ТОП-10</b>\n\n"

        medals = ["🥇", "🥈", "🥉"]

        for idx, entry in enumerate(leaderboard, 1):
            medal = medals[idx - 1] if idx <= 3 else f"{idx}."

            # Ім'я БЕЗ нікнейму, НЕ клікабельне
            name = entry.get('first_name', 'Користувач')
            refs_count = entry.get('referrals_count', 0)

            # Позначити поточного користувача
            if entry.get('telegram_id') == user_id:
                text += f"{medal} {name} (ви) ⭐ - {refs_count} рефералів\n"
            else:
                text += f"{medal} {name} - {refs_count} рефералів\n"

        text += "\n💡 Запрошуйте друзів та виграйте\n"
        text += "   щомісячні призи!"

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_referral")]
            ]),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in ref_leaderboard: {e}")
        await callback.answer("❌ Помилка завантаження рейтингу", show_alert=True)


@router.callback_query(F.data.startswith("ref_list_"))
async def referral_list(callback: CallbackQuery):
    """Список рефералів з пагінацією"""
    page = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    try:
        # Отримати рефералів
        referrals = await api_client.get(f"/api/users/{user_id}/referrals")

        if not referrals:
            await callback.message.edit_text(
                "📋 <b>МОЇ РЕФЕРАЛИ</b>\n\n"
                "У вас поки немає рефералів.\n\n"
                "Поділіться своїм посиланням з друзями!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_referral")]
                ]),
                parse_mode="HTML"
            )
            return

        # Пагінація
        per_page = 10
        total = len(referrals)
        total_pages = (total + per_page - 1) // per_page

        start_idx = page * per_page
        end_idx = min(start_idx + per_page, total)

        page_referrals = referrals[start_idx:end_idx]

        text = f"📋 <b>МОЇ РЕФЕРАЛИ ({total})</b>\n\n"
        text += f"Сторінка {page + 1} з {total_pages}\n\n"

        for idx, ref in enumerate(page_referrals, start=start_idx + 1):
            ref_id = ref.get('telegram_id')
            first_name = ref.get('first_name', 'Користувач')
            is_active = ref.get('is_active', False)
            created_at = ref.get('created_at', '')

            # Клікабельне ім'я
            name_link = f'<a href="tg://user?id={ref_id}">{first_name}</a>'

            status = "активний" if is_active else "неактивний"

            # Форматування дати
            try:
                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = date_obj.strftime('%d.%m.%Y')
            except:
                date_str = "Невідомо"

            text += f"{idx}. {name_link} - {status}\n"
            text += f"   Реєстрація: {date_str}\n\n"

        # Кнопки навігації
        keyboard = []
        nav_buttons = []

        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"ref_list_{page - 1}"
            ))

        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="▶️ Далі",
                callback_data=f"ref_list_{page + 1}"
            ))

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton(text="⬅️ До реферальної програми", callback_data="settings_referral")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in ref_list: {e}")
        await callback.answer("❌ Помилка завантаження списку", show_alert=True)


@router.callback_query(F.data == "ref_notif_on")
async def enable_ref_notifications(callback: CallbackQuery):
    """Увімкнути сповіщення про рефералів"""
    try:
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {"referral_notifications_enabled": True}
        )
        await callback.answer("🔔 Сповіщення увімкнено", show_alert=True)
        await settings_referral(callback)
    except Exception as e:
        logger.error(f"Error enabling ref notif: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(F.data == "ref_notif_off")
async def disable_ref_notifications(callback: CallbackQuery):
    """Вимкнути сповіщення про рефералів"""
    try:
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {"referral_notifications_enabled": False}
        )
        await callback.answer("🔕 Сповіщення вимкнено", show_alert=True)
        await settings_referral(callback)
    except Exception as e:
        logger.error(f"Error disabling ref notif: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


# ========== 5. ВИДАЛЕННЯ АКАУНТУ ==========
@router.callback_query(F.data == "settings_delete")
async def settings_delete_step1(callback: CallbackQuery):
    """Крок 1: Спроба відмовити від видалення"""
    text = (
        "🗑️ <b>ВИДАЛЕННЯ АКАУНТУ</b>\n\n"
        "⚠️ <b>Зачекайте! Перед видаленням...</b>\n\n"
        "✅ Ми НЕ продаємо ваші дані\n"
        "✅ Ми НЕ використовуємо дані для реклами\n"
        "✅ Ми НЕ спамимо в боті\n"
        "✅ Ваші дані захищені\n\n"
        "💡 Можливо просто вимкнути сповіщення?\n"
        "   Ви завжди зможете їх увімкнути назад!"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Налаштувати сповіщення", callback_data="settings_notifications")],
        [InlineKeyboardButton(text="🗑️ Все одно видалити", callback_data="delete_step2")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "delete_step2")
async def settings_delete_step2(callback: CallbackQuery):
    """Крок 2: Фінальне підтвердження"""
    text = (
        "⚠️ <b>ВИ ВПЕВНЕНІ?</b>\n\n"
        "При видаленні акаунту ви втратите:\n"
        "• Всю історію відключень\n"
        "• Статистику та аналітику\n"
        "• Реферальні бонуси\n"
        "• Підписку STANDARD/PRO\n\n"
        "Ви завжди можете повернутися!\n"
        "Просто натисніть /start"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="settings_back")],
        [InlineKeyboardButton(text="🗑️ Так, видалити назавжди", callback_data="delete_confirm")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "delete_confirm")
async def settings_delete_confirm(callback: CallbackQuery):
    """Крок 3: Видалення акаунту"""
    user_id = callback.from_user.id

    try:
        # Видалити користувача через API
        await api_client.delete(f"/api/users/{user_id}")

        await callback.message.edit_text(
            "✅ <b>АКАУНТ ВИДАЛЕНО</b>\n\n"
            "Всі ваші дані видалено з системи.\n\n"
            "Сумуватимемо за вами! 😢\n\n"
            "Якщо передумаєте - просто /start",
            parse_mode="HTML"
        )

        logger.info(f"User {user_id} deleted their account")

    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        await callback.message.edit_text(
            "❌ Помилка видалення акаунту.\n\n"
            "Спробуйте пізніше або зверніться в підтримку.",
            reply_markup=get_back_to_settings_keyboard()
        )

    await callback.answer()