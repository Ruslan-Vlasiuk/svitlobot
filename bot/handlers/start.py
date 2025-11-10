from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from utils.admin_notifier import notify_admin_new_address

import logging

from config import settings
from api_client import api_client
from keyboards.reply import (
    get_main_keyboard,
    get_address_method_keyboard,
    get_cancel_keyboard
)
from keyboards.inline import (
    get_subscription_keyboard,
    get_queue_selection
)
from states import RegistrationStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Обработка команды /start

    Сценарий:
    1. Проверить существует ли пользователь
    2. Если нет - создать и начать регистрацию
    3. Если да - показать главное меню
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    try:
        # Попытка получить пользователя
        user = await api_client.get_user(user_id)

        # Пользователь существует
        await state.clear()
        await message.answer(
            f"👋 З поверненням, {first_name}!\n\n"
            f"Раді бачити Вас знову в СвітлоБот!",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Existing user {user_id} returned")

    except Exception as e:
        # Пользователь не существует - создаём
        logger.info(f"New user {user_id}, starting registration")

        try:
            await api_client.create_user(
                user_id=user_id,
                username=username,
                first_name=first_name
            )

            # Начать регистрацию - проверка подписки
            await message.answer(
                f"👋 Вітаємо в СвітлоБот, {first_name}!\n\n"
                f"🔔 Для отримання доступу підпішіться на канал:",
                reply_markup=get_subscription_keyboard(settings.TELEGRAM_CHANNEL_USERNAME)
            )

            # Установить состояние
            await state.set_state(RegistrationStates.waiting_for_subscription)

        except Exception as create_error:
            logger.error(f"Failed to create user {user_id}: {create_error}")
            await message.answer(
                "❌ Виникла помилка при реєстрації.\n"
                "Спробуйте пізніше або зверніться в підтримку."
            )


@router.callback_query(RegistrationStates.waiting_for_subscription, F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    """Проверка подписки на канал"""
    user_id = callback.from_user.id

    try:
        # Проверить подписку через API Telegram
        member = await callback.bot.get_chat_member(
            chat_id=settings.TELEGRAM_CHANNEL_ID,
            user_id=user_id
        )

        # Статусы: creator, administrator, member = подписан
        # left, kicked = не подписан
        if member.status in ['creator', 'administrator', 'member']:
            await callback.answer("✅ Підписка підтверджена!", show_alert=True)

            # Переход к выбору способа ввода адреса
            await callback.message.edit_text(
                "✅ Дякуємо за підписку!\n\n"
                "Тепер давайте визначимо вашу адресу, щоб дізнатися до якої черги ви належите."
            )

            await callback.message.answer(
                "🏠 Оберіть спосіб визначення вашої адреси:",
                reply_markup=get_address_method_keyboard()
            )

            await state.set_state(RegistrationStates.choosing_address_method)
        else:
            await callback.answer(
                "❌ Ви ще не підписалися на канал.\n"
                "Будь ласка, підпішіться та спробуйте знову.",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"Failed to check subscription for {user_id}: {e}")
        await callback.answer(
            "❌ Помилка перевірки підписки. Спробуйте ще раз.",
            show_alert=True
        )


@router.message(RegistrationStates.choosing_address_method, F.text == "📍 Визначити місцезнаходження")
async def show_location_instruction(message: Message, state: FSMContext):
    """Показать инструкцию как отправить геолокацию"""
    logger.info(f"🔵 User {message.from_user.id} pressed location button")
    await message.answer(
        "📍 <b>Як надіслати геолокацію:</b>\n\n"
        "1️⃣ Натисніть на кнопку <b>📎</b> (скріпка) внизу\n"
        "2️⃣ Оберіть <b>📍 Місце</b>\n"
        "3️⃣ Надішліть вашу поточну геопозицію\n\n"
        "⏳ Очікую геолокацію...",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    logger.info(f"✅ Instruction sent to {message.from_user.id}")


@router.message(RegistrationStates.choosing_address_method, F.text == "❌ Скасувати")
async def cancel_address_input(message: Message, state: FSMContext):
    """Отмена ввода адреса"""
    logger.info(f"❌ User {message.from_user.id} cancelled address input")

    await message.answer(
        "❌ Скасовано\n\n"
        "Оберіть спосіб визначення вашої адреси:",
        reply_markup=get_address_method_keyboard()
    )

    # Остаемся в том же state - выбор способа ввода адреса
    await state.set_state(RegistrationStates.choosing_address_method)


@router.message(RegistrationStates.choosing_address_method, F.text == "✍️ Ввести вручну")
async def address_manual_input(message: Message, state: FSMContext):
    """Ручной ввод адреса"""
    await message.answer(
        "📝 Введіть вашу вулицю:\n\n"
        "Приклад: вул. Соборна",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(RegistrationStates.entering_street)


@router.message(RegistrationStates.choosing_address_method, F.text == "🔢 Я знаю свою чергу")
async def address_queue_input(message: Message, state: FSMContext):
    """Прямой выбор черги"""
    await message.answer(
        "🔢 Оберіть вашу чергу:",
        reply_markup=get_queue_selection()
    )
    await state.set_state(RegistrationStates.choosing_queue)

@router.message(RegistrationStates.entering_street)
async def process_street_input(message: Message, state: FSMContext):
    """Обработка ввода улицы с нечётким поиском"""
    # Проверка на отмену
    if message.text == "❌ Скасувати":
        await message.answer(
            "❌ Введення скасовано.\n\n"
            "Оберіть спосіб визначення вашої адреси:",
            reply_markup=get_address_method_keyboard()
        )
        await state.set_state(RegistrationStates.choosing_address_method)
        return

    street_input = message.text.strip()

    try:
        # Поиск улицы с нечётким поиском (автокоррекция опечаток)
        result = await api_client.get(f"/api/addresses/streets?prefix={street_input}")
        logger.info(f"🔍 Street search for '{street_input}': {result}")

        if result and len(result) > 0:
            # Улица найдена (берём первый результат - самый релевантный)
            found_street = result[0]
            await state.update_data(street=found_street)

            await message.answer(
                f"📍 Вулиця знайдена: {found_street}\n\n"
                f"Тепер введіть номер будинку:\n"
                f"Приклад: 12 або 7А",
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(RegistrationStates.entering_house)
        else:
            # Улица не найдена
            await message.answer(
                f"❌ Вулицю \"{street_input}\" не знайдено в базі.\n\n"
                f"Спробуйте ввести по-іншому або оберіть чергу вручну:",
                reply_markup=get_address_method_keyboard()
            )

    except Exception as e:
        logger.error(f"Error searching street: {e}")
        await message.answer(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_cancel_keyboard()
        )


@router.message(RegistrationStates.entering_house)
async def process_house_input(message: Message, state: FSMContext):
    """Обработка ввода номера дома"""
    # Проверка на отмену
    if message.text == "❌ Скасувати":
        await message.answer(
            "❌ Введення скасовано.\n\n"
            "Оберіть спосіб визначення вашої адреси:",  # ← убрать "🏠"
            reply_markup=get_address_method_keyboard()
        )
        await state.set_state(RegistrationStates.choosing_address_method)
        return

    house = message.text.strip()
    data = await state.get_data()
    street = data.get("street")

    try:
        # Поиск точного адреса
        result = await api_client.get(
            f"/api/addresses/exact?street={street}&house_number={house}"
        )

        if result and result.get("id"):
            # Адрес найден
            queue_id = result["queue_id"]
            address_id = result["id"]

            # Обновить пользователя
            await api_client.patch(
                f"/api/users/{message.from_user.id}",
                {
                    "primary_address_id": address_id,
                    "subscription_tier": "FREE"
                }
            )

            await state.clear()
            await message.answer(
                f"✅ Реєстрація завершена!\n\n"
                f"📍 Ваша адреса: {street}, {house}\n"
                f"🔢 Черга: {queue_id}\n\n"
                f"Ви будете отримувати сповіщення про відключення та увімкнення світла.",
                reply_markup=get_main_keyboard()
            )
        else:
            # Адрес не найден - предложить выбрать чергу вручную
            await message.answer(
                f"❌ Будинок \"{house}\" на вулиці \"{street}\" не знайдено в базі.\n\n"
                f"🔢 Будь ласка, оберіть вашу чергу вручну.\n"
                f"📝 Цей адрес буде доданий до бази після перевірки адміністратором.",
                reply_markup=get_queue_selection()
            )
            await state.update_data(street=street, house=house)
            await state.set_state(RegistrationStates.choosing_queue)

    except Exception as e:
        logger.error(f"Error searching address: {e}")
        await message.answer(
            "❌ Помилка пошуку. Спробуйте ще раз.",
            reply_markup=get_cancel_keyboard()
        )


@router.callback_query(RegistrationStates.choosing_queue, F.data.startswith("queue_"))
async def process_queue_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора черги"""
    queue_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    street = data.get("street")
    house = data.get("house")

    try:
        # Если есть street и house - создать новый адрес
        if street and house:
            address = await api_client.post(
                "/api/addresses/",
                {
                    "street": street,
                    "house_number": house,
                    "queue_id": queue_id
                }
            )
            address_id = address["id"]

            # ✅ Уведомити адміна про новий адрес
            await notify_admin_new_address(
                bot=callback.bot,
                user_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                street=street,
                house=house,
                queue_id=queue_id
            )
        else:
            address_id = None

        # Обновить пользователя
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {
                "primary_address_id": address_id,
                "subscription_tier": "FREE"
            }
        )

        await state.clear()

        if address_id:
            await callback.message.edit_text(
                f"✅ Реєстрація завершена!\n\n"
                f"📍 Адреса: {street}, {house}\n"
                f"🔢 Черга: {queue_id}\n\n"
                f"Адресу додано до бази даних."
            )
        else:
            await callback.message.edit_text(
                f"✅ Реєстрація завершена!\n\n"
                f"🔢 Черга: {queue_id}\n\n"
                f"Ви будете отримувати сповіщення для цієї черги."
            )

        await callback.message.answer(
            "Головне меню:",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Error selecting queue: {e}")
        await callback.answer(
            "❌ Помилка збереження черги. Спробуйте ще раз.",
            show_alert=True
        )


@router.message(Command("start_develop"))
async def cmd_start_develop(message: Message, state: FSMContext):
    """
    СЕКРЕТНАЯ команда для разработки
    Начинает регистрацию заново (даже если пользователь существует)
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    logger.info(f"🔧 DEV MODE: User {user_id} restarting registration")

    # Очистить состояние FSM
    await state.clear()

    try:
        # Попытка создать пользователя (если не существует)
        try:
            await api_client.create_user(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
        except:
            # Пользователь уже существует - ничего страшного
            pass

        # Начать регистрацию заново
        await message.answer(
            f"🔧 DEV MODE: Перезапуск регистрації\n\n"
            f"👋 Вітаємо в СвітлоБот, {first_name}!\n\n"
            f"🔔 Для доступу до бота підпішіться на канал:",
            reply_markup=get_subscription_keyboard(settings.TELEGRAM_CHANNEL_USERNAME)
        )

        # Установить состояние
        await state.set_state(RegistrationStates.waiting_for_subscription)

    except Exception as e:
        logger.error(f"Failed to restart registration for {user_id}: {e}")
        await message.answer(
            "❌ Виникла помилка. Спробуйте ще раз.",
            reply_markup=get_main_keyboard()
        )


@router.callback_query(F.data == "cancel_registration")
async def cancel_registration_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки Скасувати"""
    # Очищаем состояние FSM
    await state.clear()

    # Удаляем сообщение с inline-кнопкой
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Отправляем новое сообщение
    await callback.message.answer(
        "❌ Реєстрація скасована.\n"
        "Натисніть /start щоб почати знову.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Подтверждаем callback
    await callback.answer()

