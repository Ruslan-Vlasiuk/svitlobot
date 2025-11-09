"""
Обробники для краудрепортів про стан електроенергії
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from api_client import api_client
from states import CrowdReportStates
from keyboards.reply import get_main_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "⚡ Повідомити про світло")
async def start_crowdreport(message: Message, state: FSMContext):
    """
    Початок процесу краудрепорту.
    Перевіряє чи користувач має прив'язану адресу/чергу.
    """
    try:
        # Отримати дані користувача
        user = await api_client.get(f"/api/users/{message.from_user.id}")

        if not user:
            await message.answer("❌ Помилка: користувача не знайдено.")
            return

        # Перевірити чи є primary_address_id
        if not user.get('primary_address_id'):
            await message.answer(
                "❌ <b>Адресу не вказано</b>\n\n"
                "Спочатку завершіть реєстрацію та вкажіть вашу адресу.\n"
                "Використайте /start для початку.",
                parse_mode="HTML"
            )
            return

        # Отримати інформацію про адресу та чергу
        address = await api_client.get(f"/api/addresses/{user['primary_address_id']}")

        if not address:
            await message.answer("❌ Помилка: адресу не знайдено в базі.")
            return

        queue_id = address['queue_id']
        address_id = address['id']

        # Зберегти queue_id, address_id и адрес у state для наступного кроку
        await state.update_data(
            queue_id=queue_id,
            address_id=address_id,
            address_street=f"{address['street']}, {address['house_number']}"
        )

        # Показати кнопки вибору
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Світло є",
                    callback_data="crowdreport_on"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Світла немає",
                    callback_data="crowdreport_off"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Скасувати",
                    callback_data="crowdreport_cancel"
                )
            ]
        ])

        await message.answer(
            "⚡ <b>Яка ситуація зі світлом?</b>\n\n"
            f"📍 Ваша адреса: {address['street']}, {address['house_number']}\n"
            f"🔢 Черга: {queue_id}\n\n"
            "Оберіть поточний стан:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        await state.set_state(CrowdReportStates.waiting_for_status)

    except Exception as e:
        logger.error(f"Error starting crowdreport for {message.from_user.id}: {e}")
        await message.answer(
            "❌ Виникла помилка. Спробуйте пізніше.",
            reply_markup=get_main_keyboard()
        )


@router.callback_query(
    CrowdReportStates.waiting_for_status,
    F.data.in_(["crowdreport_on", "crowdreport_off"])
)
async def ask_confirmation(callback: CallbackQuery, state: FSMContext):
    """
    Запросити підтвердження перед збереженням репорту.
    """
    try:
        # Определить выбранный статус
        report_type = "power_on" if callback.data == "crowdreport_on" else "power_off"

        # Сохранить выбор в state
        data = await state.get_data()
        await state.update_data(report_type=report_type)

        status_emoji = "✅" if report_type == "power_on" else "❌"
        status_text = "Світло є" if report_type == "power_on" else "Світла немає"

        # Показать подтверждение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Підтвердити",
                    callback_data="crowdreport_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="crowdreport_cancel"
                )
            ]
        ])

        await callback.message.edit_text(
            f"⚡ <b>Підтвердження</b>\n\n"
            f"{status_emoji} Ви повідомляєте: <b>{status_text}</b>\n\n"
            f"📍 Адреса: {data.get('address_street', 'Ваша адреса')}\n"
            f"🔢 Черга: {data.get('queue_id')}\n\n"
            f"Підтвердити відправку?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in ask_confirmation: {e}")
        await callback.answer("❌ Помилка", show_alert=True)


@router.callback_query(
    CrowdReportStates.waiting_for_status,
    F.data == "crowdreport_confirm"
)
async def process_crowdreport(callback: CallbackQuery, state: FSMContext):
    """
    Обробка підтвердження та збереження репорту у БД.
    """
    try:
        data = await state.get_data()
        report_type = data.get('report_type')
        queue_id = data.get('queue_id')
        address_id = data.get('address_id')

        if not report_type:
            await callback.answer("❌ Помилка: статус не вибрано", show_alert=True)
            return

        # Зберегти репорт з address_id
        report = await api_client.post(
            "/api/crowdreports/",
            {
                "user_id": callback.from_user.id,
                "address_id": address_id,
                "queue_id": queue_id,
                "report_type": report_type
            }
        )

        # Отримати статистику за останні 30 хвилин
        stats = await api_client.get(
            f"/api/crowdreports/stats?queue_id={queue_id}&minutes=30"
        )

        status_emoji = "✅" if report_type == "power_on" else "❌"
        status_text = "Світло є" if report_type == "power_on" else "Світла немає"

        response_text = (
            f"✅ <b>Дякуємо за повідомлення!</b>\n\n"
            f"{status_emoji} <b>{status_text}</b>\n\n"
            f"📊 <b>Статистика по черзі {queue_id}</b>\n"
            f"(за останні 30 хвилин):\n\n"
            f"• Повідомили про увімкнення: {stats.get('on_count', 0)}\n"
            f"• Повідомили про відключення: {stats.get('off_count', 0)}\n\n"
            f"⏰ Оновлено: {datetime.now().strftime('%H:%M')}"
        )

        await callback.message.edit_text(
            response_text,
            parse_mode="HTML"
        )

        await callback.message.answer(
            "Повернутися до головного меню:",
            reply_markup=get_main_keyboard()
        )

        await state.clear()

        logger.info(
            f"Crowdreport saved: user={callback.from_user.id}, "
            f"queue={queue_id}, report_type={report_type}"
        )

    except Exception as e:
        logger.error(f"Error processing crowdreport: {e}")
        await callback.answer("❌ Помилка збереження репорту", show_alert=True)
        await state.clear()


@router.callback_query(
    CrowdReportStates.waiting_for_status,
    F.data == "crowdreport_cancel"
)
async def cancel_crowdreport(callback: CallbackQuery, state: FSMContext):
    """Скасування краудрепорту"""
    await callback.message.edit_text("❌ Скасовано")
    await callback.message.answer(
        "Повернутися до головного меню:",
        reply_markup=get_main_keyboard()
    )
    await state.clear()