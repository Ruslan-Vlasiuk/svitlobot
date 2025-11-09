# DEVELOPMENT ROADMAP: СвітлоБот

**Version:** 1.0  
**Date:** 2025-11-08  
**Timeline:** 2 дні (48 годин)  
**Status:** Ready to start

---

## ЗМІСТ

1. [Огляд](#огляд)
2. [День 1: Backend + Infrastructure](#день-1-backend--infrastructure)
3. [День 2: Bot + Features](#день-2-bot--features)
4. [Контрольний список](#контрольний-список)
5. [Критичні функції](#критичні-функції)
6. [Можливі ризики](#можливі-ризики)

---

## ОГЛЯД

### Стратегія розробки
- **Метод:** Поетапна розробка з тестуванням після кожного кроку
- **Пріоритет:** Спочатку критичні функції (NOFREE/FREE/STANDARD), потім PRO
- **Тестування:** Після кожного кроку копіюємо на VPS та тестуємо

### Розподіл часу
```
День 1 (24 год):
├── Infrastructure (4 год)
├── Backend Core (6 год)
├── Database Models (4 год)
├── API Endpoints (6 год)
└── Testing & Fixes (4 год)

День 2 (24 год):
├── Telegram Bot (8 год)
├── Notifications (4 год)
├── Payments & Referrals (4 год)
├── Admin Bot (3 год)
├── Excel Integration (2 год)
└── Final Testing (3 год)
```

---

## ДЕНЬ 1: BACKEND + INFRASTRUCTURE

### ⏰ КРОК 1: Infrastructure Setup (4 години)

**Завдання:**
1. Підготувати VPS
2. Встановити Docker + Docker Compose
3. Налаштувати .env
4. Створити docker-compose.yml
5. Запустити PostgreSQL + Redis

**Файли для створення:**
```
svetlobot/
├── .env
├── docker-compose.yml
└── README.md
```

**Код:**

**.env:**
```bash
# DATABASE
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=svetlobot
POSTGRES_USER=svetlobot_user
POSTGRES_PASSWORD=change_me_strong_password_123

DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# REDIS
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=change_me_redis_password_456
REDIS_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0

# TELEGRAM
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_BOT_TOKEN=your_admin_bot_token_here
TELEGRAM_CHANNEL_ID=-1001234567890
ADMIN_USER_IDS=123456789

# BACKEND
API_HOST=0.0.0.0
API_PORT=8000
ADMIN_API_TOKEN=change_me_admin_token_789

# LIQPAY
LIQPAY_PUBLIC_KEY=sandbox_i12345678
LIQPAY_PRIVATE_KEY=sandbox_your_private_key_here

# IOT
IOT_API_KEY=change_me_iot_key_abc123
```

**docker-compose.yml:** (див. DEPLOYMENT_GUIDE.md)

**Тестування:**
```bash
docker compose up -d postgres redis
docker compose ps  # Має бути: Up (healthy)
```

**Результат:** ✅ Інфраструктура готова

---

### ⏰ КРОК 2: Backend Core (6 годин)

**Завдання:**
1. Створити структуру backend/
2. Налаштувати FastAPI
3. Підключення до PostgreSQL
4. Підключення до Redis
5. Базові endpoints (/health, /docs)

**Файли для створення:**
```
backend/
├── Dockerfile
├── requirements.txt
├── main.py
├── database.py
├── redis_client.py
├── config.py
└── alembic.ini
```

**Код:**

**requirements.txt:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.12.1
pydantic==2.5.0
pydantic-settings==2.1.0
redis==5.0.1
python-multipart==0.0.6
aiohttp==3.9.0
pandas==2.1.3
openpyxl==3.1.2
celery==5.3.4
```

**main.py:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="СвітлоБот API",
    description="Backend для Telegram-бота моніторингу електропостачання",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "СвітлоБот API v1.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

**database.py:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=40
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

**config.py:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    ADMIN_BOT_TOKEN: str
    TELEGRAM_CHANNEL_ID: int
    ADMIN_USER_IDS: str
    
    # API
    ADMIN_API_TOKEN: str
    
    # LiqPay
    LIQPAY_PUBLIC_KEY: str
    LIQPAY_PRIVATE_KEY: str
    
    # IoT
    IOT_API_KEY: str
    
    # Other
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**Тестування:**
```bash
docker compose up -d backend
curl http://localhost:8000/health
# Має повернути: {"status":"healthy"}
```

**Результат:** ✅ Backend запущений

---

### ⏰ КРОК 3: Database Models (4 години)

**Завдання:**
1. Створити SQLAlchemy моделі
2. Налаштувати Alembic
3. Виконати міграції
4. Створити початкові черги

**Файли для створення:**
```
backend/models/
├── __init__.py
├── user.py
├── queue.py
├── address.py
├── notification.py
├── payment.py
├── referral.py
├── crowdreport.py
└── iot_sensor.py
```

**Код (приклад user.py):**
```python
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, JSON
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(100))
    first_name = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Підписка
    subscription_tier = Column(String(20), nullable=False, default='NOFREE')
    subscription_expires_at = Column(DateTime(timezone=True))
    is_channel_subscribed = Column(Boolean, default=False)
    last_subscription_check = Column(DateTime(timezone=True))
    
    # Локація
    primary_address_id = Column(Integer)
    address_count = Column(Integer, default=1)
    
    # Реферали
    referred_by = Column(BigInteger)
    referral_code = Column(String(20), unique=True)
    referral_count = Column(Integer, default=0)
    referral_days_earned = Column(Integer, default=0)
    
    # Налаштування
    settings = Column(JSON, default={
        "warning_times": [5, 10, 15, 30, 60, 120],
        "notifications_enabled": True,
        "night_mode": False
    })
    
    # Статистика
    total_notifications_sent = Column(Integer, default=0)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now())
    is_blocked = Column(Boolean, default=False)
```

**Міграції:**
```bash
# В контейнері backend
docker compose exec backend alembic init alembic
docker compose exec backend alembic revision --autogenerate -m "Initial models"
docker compose exec backend alembic upgrade head
```

**Створення черг:**
```python
# Скрипт: backend/init_queues.py
from database import AsyncSessionLocal
from models.queue import Queue

async def init_queues():
    async with AsyncSessionLocal() as db:
        for i in range(1, 13):
            queue = Queue(
                queue_id=i,
                name=f"Черга {i}",
                is_power_on=True
            )
            db.add(queue)
        await db.commit()

# Запустити:
docker compose exec backend python init_queues.py
```

**Результат:** ✅ База даних готова

---

### ⏰ КРОК 4: API Endpoints (6 годин)

**Завдання:**
1. Створити endpoints для користувачів
2. Створити endpoints для черг
3. Створити endpoints для адрес
4. Створити endpoints для сповіщень
5. Створити endpoints для IoT

**Файли для створення:**
```
backend/api/
├── __init__.py
├── users.py
├── queues.py
├── addresses.py
├── notifications.py
└── iot.py
```

**Код (приклад users.py):**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["Users"])

class UserCreate(BaseModel):
    user_id: int
    username: str | None = None
    first_name: str | None = None

@router.post("/")
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Перевірити чи існує
    existing = await db.get(User, user_data.user_id)
    if existing:
        return {"message": "User already exists", "user_id": user_data.user_id}
    
    # Створити
    user = User(
        user_id=user_data.user_id,
        username=user_data.username,
        first_name=user_data.first_name,
        referral_code=generate_referral_code()
    )
    db.add(user)
    await db.commit()
    
    return {"message": "User created", "user_id": user.user_id}

@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
```

**Підключити роутери в main.py:**
```python
from api import users, queues, addresses, notifications, iot

app.include_router(users.router)
app.include_router(queues.router)
app.include_router(addresses.router)
app.include_router(notifications.router)
app.include_router(iot.router)
```

**Тестування:**
```bash
# Створити користувача
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"user_id":123456789,"first_name":"Test"}'

# Отримати користувача
curl http://localhost:8000/api/users/123456789
```

**Результат:** ✅ API endpoints працюють

---

## ДЕНЬ 2: BOT + FEATURES

### ⏰ КРОК 5: Telegram Bot Core (8 годин)

**Завдання:**
1. Створити структуру bot/
2. Налаштувати Aiogram 3
3. Створити handlers (start, info, settings)
4. Створити keyboards (reply, inline)
5. Налаштувати FSM states
6. Інтеграція з Backend API

**Файли для створення:**
```
bot/
├── Dockerfile
├── requirements.txt
├── main.py
├── handlers/
│   ├── __init__.py
│   ├── start.py
│   ├── info.py
│   └── settings.py
├── keyboards/
│   ├── __init__.py
│   ├── reply.py
│   └── inline.py
├── states.py
└── api_client.py
```

**requirements.txt:**
```
aiogram==3.2.0
aiohttp==3.9.0
redis==5.0.1
```

**main.py:**
```python
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from config import settings
from handlers import start, info, settings as settings_handler

async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    
    # Підключити handlers
    dp.include_router(start.router)
    dp.include_router(info.router)
    dp.include_router(settings_handler.router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

**handlers/start.py:**
```python
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from keyboards.reply import get_main_keyboard
from api_client import APIClient

router = Router()
api = APIClient()

@router.message(CommandStart())
async def cmd_start(message: Message):
    # Створити користувача в backend
    await api.create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    # Привітання
    await message.answer(
        "👋 Вітаємо у СвітлоБот!\n\n"
        "Я допоможу вам отримувати оперативні сповіщення "
        "про відключення та увімкнення світла у вашому районі.",
        reply_markup=get_main_keyboard()
    )
```

**keyboards/reply.py:**
```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="📊 Інформація")],
        [KeyboardButton(text="⚙️ Налаштування"), KeyboardButton(text="🎁 Тарифи")],
        [KeyboardButton(text="👥 Запросити друзів"), KeyboardButton(text="ℹ️ Про бота")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
```

**Тестування:**
```bash
docker compose up -d bot
# Відкрити Telegram → /start
```

**Результат:** ✅ Бот відповідає

---

### ⏰ КРОК 6: Notification System (4 години)

**Завдання:**
1. Створити NotificationService
2. Налаштувати Celery
3. Створити task для розсилки
4. Протестувати масову розсилку

**Файли для створення:**
```
backend/services/
└── notification_service.py

backend/tasks/
├── __init__.py
└── notification_dispatcher.py
```

**notification_service.py:**
```python
class NotificationService:
    async def send_power_off_notification(self, queue_id: int):
        # 1. Отримати користувачів черги
        users = await self.get_users_by_queue(queue_id)
        
        # 2. Фільтр по тарифах
        eligible = [u for u in users if self.can_receive(u, 'power_off')]
        
        # 3. Текст з Excel
        template = await self.get_template('power_off')
        
        # 4. Запустити Celery task
        from tasks.notification_dispatcher import send_bulk_notification
        send_bulk_notification.delay(eligible, template, queue_id)
```

**Тестування:**
```bash
# Симуляція відключення черги 5
curl -X POST http://localhost:8000/api/notifications/send \
  -H "Content-Type: application/json" \
  -d '{"queue_id":5,"type":"power_off"}'
```

**Результат:** ✅ Сповіщення працюють

---

### ⏰ КРОК 7: Payments & Referrals (4 години)

**Завдання:**
1. Інтеграція LiqPay
2. Реферальна система
3. Обробка callback

**Файли:**
```
backend/api/
├── payments.py
└── referrals.py

backend/services/
├── payment_service.py
└── referral_service.py
```

**Тестування:**
```bash
# Створити платіж
curl -X POST http://localhost:8000/api/payments/create \
  -d '{"user_id":123456789,"tier":"PRO","months":1}'

# Активувати реферал
curl -X POST http://localhost:8000/api/referrals/activate \
  -d '{"user_id":987654321,"referral_code":"ABC123"}'
```

**Результат:** ✅ Платежі та реферали працюють

---

### ⏰ КРОК 8: Admin Bot (3 години)

**Завдання:**
1. Створити admin_bot/
2. Модерація краудрепортів
3. Масова розсилка
4. Статистика

**Результат:** ✅ Адмін-бот готовий

---

### ⏰ КРОК 9: Excel Integration (2 години)

**Завдання:**
1. Парсинг addresses.xlsx
2. Парсинг texts.xlsx
3. Автозавантаження

**Результат:** ✅ Excel працює

---

### ⏰ КРОК 10: Final Testing (3 години)

**Завдання:**
1. E2E тестування всіх функцій
2. Навантажувальне тестування
3. Виправлення багів
4. Документація

**Результат:** ✅ Проект готовий до запуску

---

## КОНТРОЛЬНИЙ СПИСОК

### День 1
- [ ] Інфраструктура (Docker, VPS)
- [ ] Backend Core (FastAPI)
- [ ] База даних (PostgreSQL)
- [ ] API Endpoints
- [ ] Celery + Redis

### День 2
- [ ] Telegram Bot
- [ ] Сповіщення
- [ ] Платежі (LiqPay)
- [ ] Реферали
- [ ] Адмін-бот
- [ ] Excel-інтеграція
- [ ] Фінальне тестування

---

## КРИТИЧНІ ФУНКЦІЇ (MVP)

**Обов'язково для запуску:**
1. ✅ Реєстрація користувача (/start)
2. ✅ Введення адреси
3. ✅ Підписка на канал
4. ✅ Фактичні сповіщення ON/OFF
5. ✅ Реферальна програма (5 днів)
6. ✅ Тарифи (FREE/STANDARD/PRO)

**Можна додати пізніше:**
- Краудрепорти
- IoT-сенсори
- WebApp карта
- Статистика

---

## МОЖЛИВІ РИЗИКИ

1. **Затримка з VPS** → Підготувати заздалегідь
2. **Баги в Telegram API** → Тестувати після кожного кроку
3. **LiqPay sandbox не працює** → Використати тестовий режим
4. **Навантаження на БД** → Додати індекси
5. **Не встигаємо все** → Пріоритизувати критичні функції

---

**Готові розпочати розробку! 🚀**