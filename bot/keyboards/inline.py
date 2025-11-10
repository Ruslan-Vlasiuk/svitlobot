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
    """
    Меню інформації (12 кнопок)

    Структура:
    - 1 широка кнопка (Графік)
    - 1 широка кнопка (Моніторинг) - З ПЕРЕНОСОМ РЯДКІВ
    - 5 пар кнопок (10 кнопок)
    """
    keyboard = [
        # 1. Графік на сьогодні (широка кнопка)
        [InlineKeyboardButton(
            text="📅 Графік на сьогодні",
            callback_data="info_schedule"
        )],

        # 2. Моніторинг мережі (широка кнопка)
        [InlineKeyboardButton(
            text="⚡ Моніторинг мережі",
            callback_data="info_monitoring"
        )],

        # 3-4. Карта міста | Точність
        [
            InlineKeyboardButton(
                text="🗺️ Карта міста",
                callback_data="info_map"
            ),
            InlineKeyboardButton(
                text="📊 Точність",
                callback_data="info_accuracy"
            )
        ],

        # 5-6. Інші міста | Підписки
        [
            InlineKeyboardButton(
                text="🤖 Інші міста",
                callback_data="info_other_bots"
            ),
            InlineKeyboardButton(
                text="💳 Підписки",
                callback_data="info_subscriptions"
            )
        ],

        # 7-8. Підтримка ЗСУ | Донат проєкту
        [
            InlineKeyboardButton(
                text="🇺🇦 Підтримка ЗСУ",
                callback_data="info_support_army"
            ),
            InlineKeyboardButton(
                text="💙 Донат проєкту",
                callback_data="info_support_project"
            )
        ],

        # 9-10. Конфіденційність | Умови
        [
            InlineKeyboardButton(
                text="🔒 Конфіденційність",
                callback_data="info_privacy"
            ),
            InlineKeyboardButton(
                text="📜 Умови користування",
                callback_data="info_terms"
            )
        ],

        # 11-12. FAQ | Підтримка
        [
            InlineKeyboardButton(
                text="❓ FAQ",
                callback_data="info_faq"
            ),
            InlineKeyboardButton(
                text="💬 Підтримка",
                callback_data="info_support"
            )
        ]
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


def get_back_to_info_keyboard():
    """Кнопка Назад в информационное меню"""
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="info_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)