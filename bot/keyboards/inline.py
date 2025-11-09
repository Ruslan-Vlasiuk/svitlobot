from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_subscription_keyboard(channel_username: str) -> InlineKeyboardMarkup:
    """Кнопка подписки на канал"""
    keyboard = [
        [InlineKeyboardButton(
            text="🔔 Підписатися на канал",
            url=f"https://t.me/{channel_username.replace('@', '')}"
        )],
        [InlineKeyboardButton(
            text="✅ Я підписався",
            callback_data="check_subscription"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_info_menu() -> InlineKeyboardMarkup:
    """Меню информации"""
    keyboard = [
        [InlineKeyboardButton(
            text="📋 Графік на сьогодні 🔒",
            callback_data="schedule_today"
        )],
        [InlineKeyboardButton(
            text="🗺️ Карта відключень 🔒",
            callback_data="outage_map"
        )],
        [InlineKeyboardButton(
            text="📊 Статистика точності 🔒",
            callback_data="accuracy_stats"
        )],
        [InlineKeyboardButton(
            text="💳 Тарифи та оплата",
            callback_data="pricing"
        )],
        [InlineKeyboardButton(
            text="❓ Часті питання",
            callback_data="faq"
        )],
        [InlineKeyboardButton(
            text="🆘 Підтримка",
            callback_data="support"
        )],
        [InlineKeyboardButton(
            text="⬅️ Закрити меню",
            callback_data="close_menu"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton(
            text="📍 Змінити адресу",
            callback_data="change_address"
        )],
        [InlineKeyboardButton(
            text="⏰ Інтервал попередження 🔒",
            callback_data="warning_times"
        )],
        [InlineKeyboardButton(
            text="💎 Мій тариф та доступ",
            callback_data="my_subscription"
        )],
        [InlineKeyboardButton(
            text="👥 Реферальна програма",
            callback_data="referral_program"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_to_main"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_queue_selection() -> InlineKeyboardMarkup:
    """Выбор черги (1-12)"""
    keyboard = []
    # По 4 кнопки в ряд
    row = []
    for i in range(1, 13):
        row.append(InlineKeyboardButton(
            text=f"Черга {i}",
            callback_data=f"queue_{i}"
        ))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(
        text="❌ Скасувати",
        callback_data="cancel"
    )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_report_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа репорта"""
    keyboard = [
        [InlineKeyboardButton(
            text="❌ Немає світла",
            callback_data="report_off"
        )],
        [InlineKeyboardButton(
            text="✅ З'явилось світло",
            callback_data="report_on"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_to_main"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение действия"""
    keyboard = [
        [InlineKeyboardButton(
            text="✅ Підтвердити",
            callback_data="confirm_yes"
        )],
        [InlineKeyboardButton(
            text="❌ Скасувати",
            callback_data="confirm_no"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_info_keyboard():
    """Клавиатура информационного меню (алиас для get_info_menu)"""
    return get_info_menu()


def get_back_keyboard():
    """Кнопка Назад в информационное меню"""
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)