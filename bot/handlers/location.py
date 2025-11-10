"""
Обробка геолокації для визначення адреси користувача
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from api_client import api_client
from states import RegistrationStates
from keyboards.reply import (
    get_address_method_keyboard,
    get_main_keyboard
)
from keyboards.inline import get_queue_selection
from utils.admin_notifier import notify_admin_new_address

logger = logging.getLogger(__name__)
router = Router()

# Ініціалізація геокодера
geolocator = Nominatim(user_agent="svetlobot_irpin", timeout=10)


@router.message(RegistrationStates.choosing_address_method, F.location)
async def process_location(message: Message, state: FSMContext):
    """
    Обробка геолокації від користувача.
    Виконує зворотнє геокодування (координати → адреса).
    ЗАВЖДИ показує похожі адреса для вибору.
    """
    logger.info(f"🟢 LOCATION HANDLER TRIGGERED for user {message.from_user.id}")
    try:
        lat = message.location.latitude
        lon = message.location.longitude

        logger.info(f"📍 Location received from {message.from_user.id}: {lat}, {lon}")

        # Відправити повідомлення про обробку
        processing_msg = await message.answer("📍 Визначаю адресу...")

        # Зворотнє геокодування
        try:
            location = geolocator.reverse(
                f"{lat}, {lon}",
                language='uk',
                exactly_one=True
            )
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Geocoding error: {e}")
            await message.answer(
                "❌ Не вдалося визначити адресу (тайм-аут сервісу).\n\n"
                "Спробуйте ще раз або введіть адресу вручну:",
                reply_markup=get_address_method_keyboard()
            )
            return

        if not location or not location.raw:
            await message.answer(
                "❌ Не вдалося визначити адресу за вказаними координатами.\n\n"
                "Можливо, ви знаходитесь за межами Ірпеня.\n"
                "Введіть адресу вручну:",
                reply_markup=get_address_method_keyboard()
            )
            return

        # Витягти компоненти адреси
        address_data = location.raw.get('address', {})

        # Можливі варіанти назв вулиць у відповіді
        street = (
            address_data.get('road') or
            address_data.get('street') or
            address_data.get('residential') or
            address_data.get('suburb') or
            ''
        )

        house = address_data.get('house_number', '')

        # Логування для дебагу
        logger.info(f"🔍 Geocoded address: {address_data}")

        if not street:
            city = address_data.get('city', address_data.get('town', 'Невідомо'))
            suburb = address_data.get('suburb', '')

            await message.answer(
                f"📍 <b>Визначено локацію:</b>\n"
                f"• Місто: {city}\n"
                f"• Район: {suburb}\n\n"
                "❌ Не вдалося визначити точну вулицю.\n\n"
                "Введіть адресу вручну:",
                parse_mode="HTML",
                reply_markup=get_address_method_keyboard()
            )
            return

        # Нормалізація назви вулиці (убрать дублирование "вул.")
        if not street.startswith('вул'):  # Проверяем без точки
            street = f"вул. {street}"

        # Пошук точного адреса в БД
        exact_address = None
        try:
            result = await api_client.get(
                f"/api/addresses/exact?street={street}&house_number={house}"
            )
            if result and result.get('id'):
                exact_address = result
                logger.info(f"✅ Exact address found: {exact_address}")
        except Exception as e:
            logger.info(f"ℹ️ Exact address not found (will show similar): {e}")

        # ЗАВЖДИ шукаємо похожі адреса
        similar_addresses = []
        try:
            similar_result = await api_client.get(
                f"/api/addresses/similar?street={street}&house_number={house}&limit=5"
            )
            if similar_result:
                similar_addresses = similar_result
                logger.info(f"🔍 Found {len(similar_addresses)} similar addresses")
        except Exception as e:
            logger.error(f"Error fetching similar addresses: {e}")

        # Якщо є точний адрес АБО похожі - показати вибір
        if exact_address or similar_addresses:
            # Формуємо inline-кнопки для вибору
            keyboard = []

            # Якщо є точний адрес - показати його ПЕРШИМ з позначкою
            if exact_address:
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"✅ Буд. {house} - Черга {exact_address['queue_id']}",
                        callback_data=f"select_addr_{exact_address['id']}"
                    )
                ])

            # Додати похожі адреса
            for addr in similar_addresses:
                if exact_address and addr['id'] == exact_address['id']:
                    continue

                keyboard.append([
                    InlineKeyboardButton(
                        text=f"📍 Буд. {addr['house_number']} - Черга {addr['queue_id']}",
                        callback_data=f"select_addr_{addr['id']}"
                    )
                ])

            # Додати кнопки для ручного вводу
            keyboard.append([
                InlineKeyboardButton(
                    text="✍️ Ввести вручну",
                    callback_data="manual_entry"
                ),
                InlineKeyboardButton(
                    text="🔢 Обрати чергу",
                    callback_data="choose_queue_manual"
                )
            ])

            # Відправити повідомлення з вибором
            await message.answer(
                f"📍 <b>Геолокацію визначено!</b>\n\n"
                f"Оберіть вашу адресу зі списку:\n"
                f"{'(✅ = рекомендована адреса)' if exact_address else ''}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )

            # Зберегти дані для подальшого використання
            await state.update_data(
                geocoded_street=street,
                geocoded_house=house
            )
            await state.set_state(RegistrationStates.selecting_from_similar)

        else:
            # Немає ні точного, ні похожих адрес - запропонувати вибір черги
            await message.answer(
                f"📍 <b>Визначено:</b> {street}, {house}\n\n"
                f"❌ На жаль, цієї адреси немає в базі даних, "
                f"і не знайдено схожих адрес.\n\n"
                f"Оберіть вашу чергу вручну:",
                parse_mode="HTML"
            )

            await message.answer(
                "🔢 Оберіть вашу чергу:",
                reply_markup=get_queue_selection()
            )

            await state.update_data(street=street, house=house)
            await state.set_state(RegistrationStates.choosing_queue)

    except Exception as e:
        logger.error(f"Error processing location: {e}", exc_info=True)
        await message.answer(
            "❌ Виникла помилка при обробці геолокації.\n\n"
            "Спробуйте ввести адресу вручну:",
            reply_markup=get_address_method_keyboard()
        )


@router.callback_query(RegistrationStates.selecting_from_similar, F.data.startswith("select_addr_"))
async def select_similar_address(callback: CallbackQuery, state: FSMContext):
    """
    Вибір адреси зі списку похожих
    """
    try:
        # Отримати address_id
        address_id = int(callback.data.split("_")[2])

        logger.info(f"✅ User {callback.from_user.id} selected address_id={address_id}")

        # Отримати інфо про адрес
        address = await api_client.get(f"/api/addresses/{address_id}")

        # Встановити адресу користувачу
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {
                "primary_address_id": address_id,
                "subscription_tier": "FREE"
            }
        )

        await state.clear()

        await callback.message.edit_text(
            f"✅ <b>Реєстрацію завершено!</b>\n\n"
            f"📍 Ваша адреса: {address['street']}, {address['house_number']}\n"
            f"🔢 Черга: {address['queue_id']}\n\n"
            "Ви будете отримувати сповіщення про відключення світла.",
            parse_mode="HTML"
        )

        await callback.message.answer(
            "Головне меню:",
            reply_markup=get_main_keyboard()
        )

        logger.info(f"✅ User {callback.from_user.id} registration completed with address_id={address_id}")

    except Exception as e:
        logger.error(f"Error selecting address: {e}")
        await callback.answer("❌ Помилка вибору адреси", show_alert=True)


@router.callback_query(RegistrationStates.selecting_from_similar, F.data == "manual_entry")
async def switch_to_manual_entry(callback: CallbackQuery, state: FSMContext):
    """
    Перехід до ручного введення адреси
    """
    logger.info(f"🔄 User {callback.from_user.id} switched to manual entry")

    await callback.message.edit_text(
        "✍️ Введіть вашу вулицю:\n\n"
        "Приклад: вул. Соборна"
    )

    await callback.message.answer(
        "Введіть адресу:",
        reply_markup=get_address_method_keyboard()
    )

    await state.set_state(RegistrationStates.entering_street)
    await callback.answer()


@router.callback_query(RegistrationStates.selecting_from_similar, F.data == "choose_queue_manual")
async def switch_to_queue_selection(callback: CallbackQuery, state: FSMContext):
    """
    Перехід до ручного вибору черги
    """
    logger.info(f"🔄 User {callback.from_user.id} switched to manual queue selection")

    data = await state.get_data()
    street = data.get('geocoded_street', '')
    house = data.get('geocoded_house', '')

    await callback.message.edit_text(
        f"📍 Визначена адреса: {street}, {house}\n\n"
        "🔢 Оберіть вашу чергу вручну:"
    )

    await callback.message.answer(
        "Оберіть чергу:",
        reply_markup=get_queue_selection()
    )

    # Зберегти дані для створення адреси
    await state.update_data(street=street, house=house)
    await state.set_state(RegistrationStates.choosing_queue)
    await callback.answer()


@router.callback_query(RegistrationStates.confirming_location, F.data.startswith("confirm_location_"))
async def confirm_location_address(callback: CallbackQuery, state: FSMContext):
    """
    Підтвердження адреси визначеної через геолокацію
    (Застарілий handler - залишений для сумісності)
    """
    try:
        # Парсимо callback_data: confirm_location_{address_id}_{queue_id}
        parts = callback.data.split("_")
        address_id = int(parts[2])
        queue_id = int(parts[3])

        logger.info(
            f"✅ User {callback.from_user.id} confirming location: "
            f"address_id={address_id}, queue={queue_id}"
        )

        # Встановлюємо адресу користувачу
        await api_client.patch(
            f"/api/users/{callback.from_user.id}",
            {
                "primary_address_id": address_id,
                "subscription_tier": "FREE"
            }
        )

        await state.clear()

        await callback.message.edit_text(
            "✅ <b>Реєстрацію завершено!</b>\n\n"
            f"🔢 Ваша черга: {queue_id}\n\n"
            "Ви будете отримувати сповіщення про відключення світла.",
            parse_mode="HTML"
        )

        await callback.message.answer(
            "Головне меню:",
            reply_markup=get_main_keyboard()
        )

        logger.info(
            f"✅ User {callback.from_user.id} registration completed via location"
        )

    except Exception as e:
        logger.error(f"Error confirming location: {e}")
        await callback.answer("❌ Помилка підтвердження адреси", show_alert=True)
        await state.clear()


@router.callback_query(RegistrationStates.confirming_location, F.data == "cancel_location")
async def cancel_location(callback: CallbackQuery, state: FSMContext):
    """
    Скасування підтвердження геолокації
    """
    logger.info(f"❌ User {callback.from_user.id} cancelled location confirmation")

    await callback.message.edit_text(
        "❌ Скасовано\n\n"
        "Оберіть інший спосіб введення адреси:"
    )

    await callback.message.answer(
        "Як ви хочете вказати адресу?",
        reply_markup=get_address_method_keyboard()
    )

    await state.set_state(RegistrationStates.choosing_address_method)
    await callback.answer()