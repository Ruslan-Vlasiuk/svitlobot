"""
Тестові команди для перемикання між тарифами
Додати до bot/handlers/dev_commands.py
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta
import logging

from api_client import api_client

logger = logging.getLogger(__name__)
router = Router()


# ========== ТЕСТОВІ КОМАНДИ ДЛЯ ЗМІНИ ТАРИФІВ ==========

@router.message(Command("trial0028"))
async def switch_to_trial(message: Message):
    """
    Перехід на TRIAL (7 днів тестового періоду)

    Логіка:
    - TRIAL - це тестовий період для нових користувачів
    - Дає доступ до функцій STANDARD на 7 днів
    - Після закінчення → FREE або NOFREE (залежно від підписки на канал)
    """
    user_id = message.from_user.id

    try:
        # Встановлюємо TRIAL на 7 днів
        expires_at = datetime.now() + timedelta(days=7)

        await api_client.patch(
            f"/api/users/{user_id}",
            {
                "subscription_tier": "TRIAL",
                "subscription_expires_at": expires_at.isoformat()
            }
        )

        await message.answer(
            "🎉 <b>ВІТАЄМО!</b>\n\n"
            "✅ Активовано <b>TRIAL підписку</b>\n\n"
            "🎁 Ви отримали:\n"
            "• 7 днів безкоштовного доступу\n"
            "• Всі можливості STANDARD\n"
            "• Налаштування періодів попереджень\n\n"
            f"📅 Діє до: {expires_at.strftime('%d.%m.%Y')}\n\n"
            "💡 Запросіть друзів щоб продовжити підписку!\n"
            "+5 днів STANDARD за кожного реферала",
            parse_mode="HTML"
        )

        logger.info(f"User {user_id} switched to TRIAL")

    except Exception as e:
        logger.error(f"Error switching to TRIAL: {e}")
        await message.answer("❌ Помилка зміни тарифу")


@router.message(Command("nofree0028"))
async def switch_to_nofree(message: Message):
    """
    Перехід на NOFREE (користувач відписався від каналу)

    Логіка:
    - Користувач був на будь-якому тарифі
    - Відписався від обов'язкового каналу
    - Втрачає ВСІ можливості бота
    - Потрібно знову підписатись щоб повернути доступ
    """
    user_id = message.from_user.id

    try:
        # Отримуємо поточний тариф
        user = await api_client.get(f"/api/users/{user_id}")
        old_tier = user.get('subscription_tier', 'FREE')

        # Встановлюємо NOFREE
        await api_client.patch(
            f"/api/users/{user_id}",
            {
                "subscription_tier": "NOFREE",
                "subscription_expires_at": None
            }
        )

        await message.answer(
            "⚠️ <b>ПІДПИСКУ ВТРАЧЕНО</b>\n\n"
            f"❌ Попередній тариф: {old_tier}\n"
            "❌ Поточний тариф: NOFREE\n\n"
            "🔴 <b>Ви відписались від обов'язкового каналу!</b>\n\n"
            "Щоб продовжити користуватись ботом:\n"
            "1. Підпишіться на канал @svitlobot_irpin\n"
            "2. Натисніть /start\n\n"
            "⚡ Без підписки бот не працює!",
            parse_mode="HTML"
        )

        logger.info(f"User {user_id} switched to NOFREE (unsubscribed)")

    except Exception as e:
        logger.error(f"Error switching to NOFREE: {e}")
        await message.answer("❌ Помилка зміни тарифу")


@router.message(Command("free0028"))
async def switch_to_free(message: Message):
    """
    Перехід на FREE

    Логіка переходів:
    - З TRIAL → FREE: закінчився тестовий період, не запросили рефералів
    - З STANDARD → FREE: закінчились бонусні дні від рефералів
    - З PRO → FREE: закінчилась оплачена підписка, не продовжили
    - З NOFREE → FREE: повторно підписались на канал
    """
    user_id = message.from_user.id

    try:
        # Отримуємо поточний тариф
        user = await api_client.get(f"/api/users/{user_id}")
        old_tier = user.get('subscription_tier', 'FREE')

        # Встановлюємо FREE
        await api_client.patch(
            f"/api/users/{user_id}",
            {
                "subscription_tier": "FREE",
                "subscription_expires_at": None
            }
        )

        # Різні повідомлення залежно від попереднього тарифу
        if old_tier == "TRIAL":
            text = (
                "⏰ <b>ТЕСТОВИЙ ПЕРІОД ЗАКІНЧИВСЯ</b>\n\n"
                "Ваш 7-денний TRIAL закінчився.\n"
                "Ви перейшли на тариф FREE.\n\n"
                "🎁 <b>Хочете STANDARD безкоштовно?</b>\n"
                "Запросіть друзів!\n"
                "+5 днів за кожного реферала\n\n"
                "📋 FREE включає:\n"
                "• 1 адреса\n"
                "• Базові сповіщення ON/OFF\n"
                "• Тихий режим"
            )
        elif old_tier == "STANDARD":
            text = (
                "⏰ <b>ПІДПИСКА STANDARD ЗАКІНЧИЛАСЬ</b>\n\n"
                "Ваші бонусні дні від рефералів закінчились.\n"
                "Ви перейшли на тариф FREE.\n\n"
                "🎁 <b>Хочете продовжити STANDARD?</b>\n"
                "Запросіть ще друзів!\n"
                "+5 днів за кожного реферала\n\n"
                "❌ Втрачено:\n"
                "• Налаштування періодів попереджень\n\n"
                "✅ Залишилось:\n"
                "• Базові сповіщення ON/OFF"
            )
        elif old_tier == "PRO":
            text = (
                "⏰ <b>ПІДПИСКА PRO ЗАКІНЧИЛАСЬ</b>\n\n"
                "Ваша оплачена підписка закінчилась.\n"
                "Ви перейшли на тариф FREE.\n\n"
                "👑 <b>Хочете продовжити PRO?</b>\n"
                "Оформіть підписку знову - до 10 грн/міс\n\n"
                "❌ Втрачено:\n"
                "• До 3 адрес одночасно\n"
                "• Критичні інсайдерські сповіщення\n"
                "• Налаштування періодів попереджень\n\n"
                "✅ Залишилось:\n"
                "• 1 адреса\n"
                "• Базові сповіщення ON/OFF"
            )
        elif old_tier == "NOFREE":
            text = (
                "✅ <b>ПІДПИСКУ ВІДНОВЛЕНО!</b>\n\n"
                "Ви знову підписались на канал.\n"
                "Тепер ви на тарифі FREE.\n\n"
                "📋 FREE включає:\n"
                "• 1 адреса\n"
                "• Базові сповіщення ON/OFF\n"
                "• Тихий режим\n\n"
                "🎁 Запросіть друзів щоб отримати STANDARD!"
            )
        else:
            text = (
                "✅ <b>ТАРИФ ЗМІНЕНО</b>\n\n"
                "Поточний тариф: FREE\n\n"
                "📋 FREE включає:\n"
                "• 1 адреса\n"
                "• Базові сповіщення ON/OFF\n"
                "• Тихий режим"
            )

        await message.answer(text, parse_mode="HTML")

        logger.info(f"User {user_id} switched from {old_tier} to FREE")

    except Exception as e:
        logger.error(f"Error switching to FREE: {e}")
        await message.answer("❌ Помилка зміни тарифу")


@router.message(Command("standard0028"))
async def switch_to_standard(message: Message):
    """
    Перехід на STANDARD

    Логіка переходів:
    - З TRIAL → STANDARD: користувач запросив 1+ рефералів
    - З FREE → STANDARD: користувач запросив 1+ рефералів
    - З PRO → STANDARD: закінчилась PRO, але є бонусні дні
    - З NOFREE → STANDARD: неможливо напряму (спочатку треба підписатись → FREE)

    Нараховуємо 5 днів (ніби 1 реферал запросив)
    """
    user_id = message.from_user.id

    try:
        # Отримуємо поточний тариф
        user = await api_client.get(f"/api/users/{user_id}")
        old_tier = user.get('subscription_tier', 'FREE')

        # Нараховуємо 5 днів (1 реферал)
        expires_at = datetime.now() + timedelta(days=5)

        # Встановлюємо STANDARD
        await api_client.patch(
            f"/api/users/{user_id}",
            {
                "subscription_tier": "STANDARD",
                "subscription_expires_at": expires_at.isoformat()
            }
        )

        # Різні повідомлення залежно від попереднього тарифу
        if old_tier in ["TRIAL", "FREE"]:
            text = (
                "🎉 <b>ВІТАЄМО!</b>\n\n"
                "✅ Ви отримали <b>STANDARD</b>!\n\n"
                "👥 Ви запросили друга через реферальне посилання\n"
                "🎁 Нараховано: <b>+5 днів</b>\n\n"
                f"📅 Діє до: {expires_at.strftime('%d.%m.%Y')}\n\n"
                "⭐ STANDARD включає:\n"
                "• Налаштування періодів попереджень\n"
                "• Все з FREE\n\n"
                "💡 Запрошуйте ще друзів!\n"
                "Кожен реферал = +5 днів\n"
                "6 рефералів = 30 днів (1 місяць)"
            )
        elif old_tier == "PRO":
            text = (
                "⏰ <b>ПІДПИСКА ЗМІНИЛАСЬ</b>\n\n"
                f"Попередній тариф: {old_tier}\n"
                "Поточний тариф: STANDARD\n\n"
                "У вас є бонусні дні від рефералів.\n"
                f"📅 Діє до: {expires_at.strftime('%d.%m.%Y')}\n\n"
                "❌ Втрачено:\n"
                "• До 3 адрес одночасно\n"
                "• Критичні інсайдерські сповіщення\n\n"
                "✅ Залишилось:\n"
                "• Налаштування періодів попереджень"
            )
        elif old_tier == "NOFREE":
            text = (
                "❌ <b>ПОМИЛКА</b>\n\n"
                "Неможливо перейти з NOFREE на STANDARD.\n\n"
                "Спочатку підпишіться на канал:\n"
                "1. /free0028 (підписка)\n"
                "2. /standard0028 (запрошення рефералів)"
            )
            await message.answer(text, parse_mode="HTML")
            return
        else:
            text = (
                "✅ <b>ТАРИФ ЗМІНЕНО</b>\n\n"
                "Поточний тариф: STANDARD\n"
                f"📅 Діє до: {expires_at.strftime('%d.%m.%Y')}"
            )

        await message.answer(text, parse_mode="HTML")

        logger.info(f"User {user_id} switched from {old_tier} to STANDARD")

    except Exception as e:
        logger.error(f"Error switching to STANDARD: {e}")
        await message.answer("❌ Помилка зміни тарифу")


@router.message(Command("pro0028"))
async def switch_to_pro(message: Message):
    """
    Перехід на PRO

    Логіка переходів:
    - З будь-якого тарифу → PRO: користувач оплатив підписку
    - Дається 30 днів (1 місяць)
    - Доступ до всіх преміум функцій
    """
    user_id = message.from_user.id

    try:
        # Отримуємо поточний тариф
        user = await api_client.get(f"/api/users/{user_id}")
        old_tier = user.get('subscription_tier', 'FREE')

        # Нараховуємо 30 днів (1 місяць)
        expires_at = datetime.now() + timedelta(days=30)

        # Встановлюємо PRO
        await api_client.patch(
            f"/api/users/{user_id}",
            {
                "subscription_tier": "PRO",
                "subscription_expires_at": expires_at.isoformat()
            }
        )

        # Різні повідомлення залежно від попереднього тарифу
        if old_tier == "NOFREE":
            text = (
                "❌ <b>ПОМИЛКА</b>\n\n"
                "Неможливо оплатити PRO без підписки на канал.\n\n"
                "Спочатку підпишіться на канал:\n"
                "1. Підпишіться на @svitlobot_irpin\n"
                "2. Натисніть /start\n"
                "3. Оформіть PRO"
            )
            await message.answer(text, parse_mode="HTML")
            return

        text = (
            "🎉 <b>ВІТАЄМО З ПОКУПКОЮ PRO!</b>\n\n"
            "✅ Підписка успішно активована\n\n"
            "💰 Списано: 10 грн\n"
            "📅 Діє до: {}\n"
            "⏰ Період: 30 днів\n\n"
            "💎 <b>PRO включає:</b>\n"
            "• До 3 адрес одночасно\n"
            "• Критичні інсайдерські сповіщення\n"
            "• Налаштування періодів попереджень\n"
            "• Все з STANDARD та FREE\n\n"
            "🔄 Автоматичне продовження: ВИМКНЕНО\n"
            "Ви можете продовжити підписку в будь-який момент"
        ).format(expires_at.strftime('%d.%m.%Y %H:%M'))

        await message.answer(text, parse_mode="HTML")

        logger.info(f"User {user_id} switched from {old_tier} to PRO")

    except Exception as e:
        logger.error(f"Error switching to PRO: {e}")
        await message.answer("❌ Помилка зміни тарифу")


# ========== ДОДАТКОВІ ТЕСТОВІ КОМАНДИ ==========

@router.message(Command("tier_info"))
async def show_tier_info(message: Message):
    """Показати поточну інформацію про тариф"""
    user_id = message.from_user.id

    try:
        user = await api_client.get(f"/api/users/{user_id}")

        tier = user.get('subscription_tier', 'FREE')
        expires = user.get('subscription_expires_at')

        text = "📊 <b>ІНФОРМАЦІЯ ПРО ТАРИФ</b>\n\n"
        text += f"🆔 Telegram ID: <code>{user_id}</code>\n"
        text += f"📋 Тариф: <b>{tier}</b>\n"

        if expires:
            try:
                expires_dt = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                expires_str = expires_dt.strftime('%d.%m.%Y %H:%M')
                days_left = (expires_dt - datetime.now()).days

                text += f"📅 Діє до: {expires_str}\n"
                text += f"⏰ Залишилось: {days_left} днів\n"
            except:
                text += "📅 Діє до: Невідомо\n"
        else:
            text += "📅 Діє до: Безстроково\n"

        text += "\n🧪 <b>Тестові команди:</b>\n"
        text += "/trial0028 - TRIAL (7 днів)\n"
        text += "/free0028 - FREE\n"
        text += "/standard0028 - STANDARD (5 днів)\n"
        text += "/pro0028 - PRO (30 днів)\n"
        text += "/nofree0028 - NOFREE (відписка)\n"

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error showing tier info: {e}")
        await message.answer("❌ Помилка отримання інформації")


@router.message(Command("reset_tier"))
async def reset_tier(message: Message):
    """Скинути тариф на FREE (для тестування)"""
    user_id = message.from_user.id

    try:
        await api_client.patch(
            f"/api/users/{user_id}",
            {
                "subscription_tier": "FREE",
                "subscription_expires_at": None
            }
        )

        await message.answer(
            "🔄 <b>ТАРИФ СКИНУТО</b>\n\n"
            "Встановлено: FREE\n\n"
            "Тепер ви можете тестувати переходи між тарифами.",
            parse_mode="HTML"
        )

        logger.info(f"User {user_id} reset tier to FREE")

    except Exception as e:
        logger.error(f"Error resetting tier: {e}")
        await message.answer("❌ Помилка скидання тарифу")