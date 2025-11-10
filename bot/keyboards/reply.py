from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню (3 кнопки Reply)

    [ℹ️ Інформація]  [⚙️ Налаштування]
    [⚡ Повідомити про світло]
    """
    keyboard = [
        [
            KeyboardButton(text="ℹ️ Інформація"),
            KeyboardButton(text="⚙️ Налаштування")
        ],
        [
            KeyboardButton(text="⚡ Повідомити про світло")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію..."
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка отмены"""
    keyboard = [[KeyboardButton(text="❌ Скасувати")]]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def get_address_method_keyboard() -> ReplyKeyboardMarkup:
    """Выбор способа ввода адреса"""
    keyboard = [
        [KeyboardButton(text="✍️ Ввести вручну")],
        [KeyboardButton(text="📍 Визначити місцезнаходження")],
        [KeyboardButton(text="🔢 Я знаю свою чергу")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Оберіть спосіб..."
    )
