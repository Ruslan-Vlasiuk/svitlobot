# TECHNICAL ARCHITECTURE: СвітлоБот

**Version:** 1.0  
**Date:** 2025-11-08  
**Target Scale:** 1,000,000 пользователей

---

## ЗМІСТ

1. [Загальна архітектура](#загальна-архітектура)
2. [Компоненти системи](#компоненти-системи)
3. [База даних](#база-даних)
4. [API endpoints](#api-endpoints)
5. [Telegram Bot](#telegram-bot)
6. [IoT-сенсори](#iot-сенсори)
7. [Система сповіщень](#система-сповіщень)
8. [Масштабування](#масштабування)
9. [Безпека](#безпека)
10. [Моніторинг](#моніторинг)

---

## ЗАГАЛЬНА АРХІТЕКТУРА

### Схема компонентів

```
┌─────────────────────────────────────────────────────────────────┐
│                         TELEGRAM BOT                            │
│                      (Aiogram 3 + Redis)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Handlers   │  │  Keyboards   │  │    States    │         │
│  │              │  │              │  │              │         │
│  │ • /start     │  │ • Reply      │  │ • Address    │         │
│  │ • /info      │  │ • Inline     │  │ • Settings   │         │
│  │ • /settings  │  │ • WebApp     │  │ • Payment    │         │
│  │ • Callbacks  │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└──────────────┬──────────────────────────────────────────────────┘
               │
               │ HTTP REST API
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Endpoints                         │  │
│  │  /api/users     /api/queues    /api/notifications       │  │
│  │  /api/payments  /api/referrals /api/crowdreports        │  │
│  │  /api/iot       /api/schedules /api/admin               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Business Logic Services                 │  │
│  │  • NotificationService  • PaymentService                 │  │
│  │  • ReferralService      • CrowdReportService             │  │
│  │  • ScheduleService      • IoTService                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Background Tasks (Celery)                  │  │
│  │  • Notification Dispatcher  • Schedule Checker           │  │
│  │  • IoT Data Processor       • Subscription Validator     │  │
│  │  • Referral Expiry          • Analytics Aggregator       │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────────────────────┘
               │
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │    Redis     │  │    Files     │         │
│  │              │  │              │  │              │         │
│  │ • Users      │  │ • Sessions   │  │ • Excel DB   │         │
│  │ • Queues     │  │ • Cache      │  │ • Logs       │         │
│  │ • Addresses  │  │ • Tasks      │  │ • Backups    │         │
│  │ • Notif.     │  │ • Rate Limit │  │              │         │
│  │ • Payments   │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
               ▲
               │
               │ 4G LTE (HTTP POST)
               │
┌─────────────────────────────────────────────────────────────────┐
│                    IoT DEVICES (ESP32)                          │
├─────────────────────────────────────────────────────────────────┤
│  24 сенсора × 12 черг = 2 сенсора на чергу                     │
│                                                                  │
│  Сенсор #1, #2, ... #24:                                        │
│  • ESP32 WROOM-32                                               │
│  • SIM7600E-H (4G LTE)                                          │
│  • Реле контроль живлення                                       │
│  • Вимірювання V/Hz (PRO-версія)                               │
│  • Відправка даних кожні 10 сек                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## КОМПОНЕНТИ СИСТЕМИ

### 1. **Telegram Bot** (Aiogram 3)

#### Handlers
```python
handlers/
├── start.py          # /start, реєстрація, привітання
├── info.py           # 📊 Інформація, графіки, карта
├── settings.py       # ⚙️ Налаштування
├── subscriptions.py  # 🎁 Тарифи, платежі
├── referral.py       # 👥 Реферали
├── crowdreports.py   # 📝 Краудрепорти
├── admin.py          # 🔧 Адмін-команди
└── callbacks.py      # Callback handlers
```

#### Keyboards
```python
keyboards/
├── reply.py          # Reply-клавіатури (головне меню)
├── inline.py         # Inline-кнопки (налаштування)
└── webapp.py         # WebApp-кнопки (карта, графіки)
```

#### States (FSM)
```python
states.py:
- AddressInput      # Введення адреси
- SettingsMenu      # Зміна налаштувань
- PaymentProcess    # Процес оплати
- CrowdReport       # Відправка репорта
- AdminModeration   # Адмін-модерація
```

#### Middlewares
```python
middlewares/
├── subscription_check.py  # Перевірка підписки на канал
├── rate_limit.py          # Rate limiting (краудрепорти)
├── logging.py             # Логування дій
└── analytics.py           # Збір метрик
```

---

### 2. **Backend API** (FastAPI)

#### Main Structure
```python
backend/
├── main.py                # FastAPI app, CORS, startup
├── database.py            # PostgreSQL connection pool
├── redis_client.py        # Redis connection
├── config.py              # Env variables
│
├── models/                # SQLAlchemy ORM models
│   ├── user.py
│   ├── queue.py
│   ├── address.py
│   ├── notification.py
│   ├── payment.py
│   ├── referral.py
│   ├── crowdreport.py
│   └── iot_sensor.py
│
├── api/                   # REST endpoints
│   ├── users.py           # CRUD користувачів
│   ├── queues.py          # Інформація про черги
│   ├── notifications.py   # Сповіщення (відправка)
│   ├── payments.py        # LiqPay інтеграція
│   ├── referrals.py       # Реферали
│   ├── crowdreports.py    # Краудрепорти
│   ├── iot.py             # IoT-сенсори (POST /iot/data)
│   ├── schedules.py       # Графіки відключень
│   └── admin.py           # Адмін-панель
│
├── services/              # Business logic
│   ├── notification_service.py
│   ├── payment_service.py
│   ├── referral_service.py
│   ├── crowdreport_service.py
│   ├── schedule_service.py
│   └── iot_service.py
│
├── tasks/                 # Celery tasks
│   ├── notification_dispatcher.py
│   ├── schedule_checker.py
│   ├── iot_processor.py
│   ├── subscription_validator.py
│   └── referral_expiry.py
│
└── utils/
    ├── excel_parser.py    # Парсинг Excel (адреси, тексти)
    ├── validators.py      # Валідація даних
    └── helpers.py         # Допоміжні функції
```

#### Key Endpoints

```python
# Користувачі
POST   /api/users                  # Реєстрація
GET    /api/users/{user_id}        # Профіль
PATCH  /api/users/{user_id}        # Оновлення (адреса, тариф)
POST   /api/users/check_subscription  # Перевірка підписки на канал

# Черги
GET    /api/queues                 # Список черг
GET    /api/queues/{queue_id}      # Інфо про чергу
GET    /api/queues/{queue_id}/status  # Статус (ON/OFF)

# Адреси
GET    /api/addresses?street=...&house=...  # Пошук адреси
POST   /api/addresses              # Додати новий (адмін)

# Сповіщення
POST   /api/notifications/send     # Відправити сповіщення
GET    /api/notifications/history  # Історія (адмін)

# Платежі
POST   /api/payments/create        # Створити LiqPay payment
POST   /api/payments/callback      # LiqPay callback
GET    /api/payments/{user_id}     # Історія платежів

# Реферали
GET    /api/referrals/{user_id}    # Статистика рефералів
POST   /api/referrals/activate     # Активація реферала

# Краудрепорти
POST   /api/crowdreports           # Надіслати репорт
GET    /api/crowdreports/pending   # Репорти на модерації (адмін)
PATCH  /api/crowdreports/{id}      # Підтвердити/відхилити (адмін)

# IoT
POST   /api/iot/data               # Дані від сенсора
GET    /api/iot/sensors            # Статус всіх сенсорів (адмін)

# Графіки
GET    /api/schedules              # Графіки на сьогодні
POST   /api/schedules              # Завантажити графік (адмін)

# Адмін
GET    /api/admin/stats            # Загальна статистика
GET    /api/admin/users?filter=... # Користувачі з фільтрами
POST   /api/admin/broadcast        # Масове повідомлення
```

---

### 3. **База даних** (PostgreSQL 14+)

#### Schema Overview

```sql
-- КОРИСТУВАЧІ
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,           -- Telegram user_id
    username VARCHAR(100),
    first_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Підписка
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'NOFREE',
                                          -- 'NOFREE', 'FREE', 'STANDARD', 'PRO'
    subscription_expires_at TIMESTAMP,    -- Для STANDARD/PRO
    is_channel_subscribed BOOLEAN DEFAULT FALSE,
    last_subscription_check TIMESTAMP,
    
    -- Локація
    primary_address_id INT,               -- FK → addresses
    address_count INT DEFAULT 1,          -- 1, 2, або 3 (PRO)
    
    -- Реферали
    referred_by BIGINT,                   -- FK → users(user_id)
    referral_code VARCHAR(20) UNIQUE,     -- Унікальний код
    referral_count INT DEFAULT 0,         -- Скільки запросив
    referral_days_earned INT DEFAULT 0,   -- Загальна кількість днів
    
    -- Налаштування сповіщень
    settings JSONB DEFAULT '{
        "warning_times": [5, 10, 15, 30, 60, 120],
        "notifications_enabled": true,
        "night_mode": false
    }',
    
    -- Статистика
    total_notifications_sent INT DEFAULT 0,
    last_active_at TIMESTAMP DEFAULT NOW(),
    is_blocked BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_users_subscription ON users(subscription_tier);
CREATE INDEX idx_users_channel ON users(is_channel_subscribed);
CREATE INDEX idx_users_referral ON users(referred_by);


-- АДРЕСИ
CREATE TABLE addresses (
    id SERIAL PRIMARY KEY,
    street VARCHAR(200) NOT NULL,
    house_number VARCHAR(20) NOT NULL,
    queue_id INT NOT NULL,                -- Номер черги (1-12)
    
    created_at TIMESTAMP DEFAULT NOW(),
    added_by VARCHAR(20) DEFAULT 'admin', -- 'admin', 'user', 'auto'
    
    UNIQUE(street, house_number)
);

CREATE INDEX idx_addresses_queue ON addresses(queue_id);
CREATE INDEX idx_addresses_street ON addresses(street);


-- ЗВ'ЯЗОК КОРИСТУВАЧІВ ТА АДРЕС (для PRO)
CREATE TABLE user_addresses (
    user_id BIGINT NOT NULL,              -- FK → users
    address_id INT NOT NULL,              -- FK → addresses
    priority INT DEFAULT 1,               -- 1, 2, 3 (порядок)
    
    PRIMARY KEY (user_id, address_id)
);


-- ЧЕРГИ
CREATE TABLE queues (
    queue_id INT PRIMARY KEY,             -- 1-12
    name VARCHAR(50),                     -- "Черга 1"
    
    -- Поточний стан
    is_power_on BOOLEAN DEFAULT TRUE,
    last_change_at TIMESTAMP,
    last_change_source VARCHAR(20),       -- 'iot', 'crowdreport', 'manual'
    
    -- Статистика
    total_outages INT DEFAULT 0,
    total_uptime_minutes INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);


-- ГРАФІКИ ВІДКЛЮЧЕНЬ
CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    queue_id INT NOT NULL,                -- FK → queues
    
    scheduled_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    
    is_confirmed BOOLEAN DEFAULT FALSE,   -- Підтверджено фактом?
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(queue_id, scheduled_date, start_time)
);

CREATE INDEX idx_schedules_date ON schedules(scheduled_date);


-- СПОВІЩЕННЯ (логування)
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,              -- FK → users
    queue_id INT NOT NULL,                -- FK → queues
    
    notification_type VARCHAR(50) NOT NULL,
                                          -- 'power_off', 'power_on',
                                          -- 'warning_60min', 'warning_30min', ...
    
    message_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT NOW(),
    
    is_delivered BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_sent ON notifications(sent_at);


-- КРАУДРЕПОРТИ
CREATE TABLE crowdreports (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,              -- FK → users
    address_id INT NOT NULL,              -- FK → addresses
    queue_id INT NOT NULL,                -- FK → queues
    
    report_type VARCHAR(20) NOT NULL,     -- 'power_on', 'power_off'
    reported_at TIMESTAMP DEFAULT NOW(),
    
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'confirmed', 'rejected'
    moderated_at TIMESTAMP,
    moderated_by BIGINT,                  -- FK → users (адмін)
    
    -- Додаткові дані
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6)
);

CREATE INDEX idx_crowdreports_status ON crowdreports(status);
CREATE INDEX idx_crowdreports_queue ON crowdreports(queue_id, reported_at);


-- IoT-СЕНСОРИ
CREATE TABLE iot_sensors (
    sensor_id VARCHAR(50) PRIMARY KEY,    -- "ESP32_001"
    queue_id INT NOT NULL,                -- FK → queues
    priority INT NOT NULL,                -- 1 або 2 (основний/резервний)
    
    -- Статус
    is_online BOOLEAN DEFAULT FALSE,
    last_ping_at TIMESTAMP,
    
    -- Технічні дані
    firmware_version VARCHAR(20),
    ip_address VARCHAR(45),
    sim_card VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT NOW()
);


-- ДАНІ ВІД СЕНСОРІВ
CREATE TABLE iot_data (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50) NOT NULL,       -- FK → iot_sensors
    
    is_power_on BOOLEAN NOT NULL,
    voltage DECIMAL(5,2),                 -- Вольтаж (для PRO)
    frequency DECIMAL(5,2),               -- Частота (для PRO)
    
    received_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_iot_data_sensor ON iot_data(sensor_id, received_at);


-- ПЛАТЕЖІ
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,              -- FK → users
    
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'UAH',
    
    payment_method VARCHAR(20),           -- 'liqpay', 'wayforpay'
    payment_id VARCHAR(100) UNIQUE,       -- ID від платіжної системи
    
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'success', 'failed'
    
    subscription_days INT NOT NULL,       -- Скільки днів додається
    subscription_tier VARCHAR(20),        -- 'STANDARD', 'PRO'
    
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);


-- РЕФЕРАЛЬНА ІСТОРІЯ
CREATE TABLE referral_activations (
    id SERIAL PRIMARY KEY,
    referrer_user_id BIGINT NOT NULL,     -- Хто запросив
    referred_user_id BIGINT NOT NULL,     -- Кого запросили
    
    days_granted INT NOT NULL DEFAULT 5,  -- Скільки днів отримав referrer
    activated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(referred_user_id)
);


-- EXCEL ТЕКСТИ (кешування)
CREATE TABLE excel_texts (
    key VARCHAR(100) PRIMARY KEY,         -- 'welcome_message', 'power_off_template', ...
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);


-- ЛОГИ ДІЙ (аудит)
CREATE TABLE action_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,                       -- NULL для системних дій
    action_type VARCHAR(50) NOT NULL,     -- 'user_registered', 'payment_success', ...
    
    description TEXT,
    metadata JSONB,                       -- Додаткові дані
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_action_logs_user ON action_logs(user_id);
CREATE INDEX idx_action_logs_type ON action_logs(action_type);
```

---

### 4. **IoT-сенсори** (ESP32)

#### Hardware
- **MCU:** ESP32 WROOM-32 (dual-core, WiFi + Bluetooth)
- **4G Modem:** SIM7600E-H (LTE Cat-4, 150 Mbps)
- **Relay Module:** для контролю живлення
- **Voltage/Frequency Sensor:** ZMPT101B + Zero-crossing detector (PRO)
- **Power:** 5V 2A (USB або блок живлення)

#### Firmware (Arduino IDE)
```cpp
// Основна логіка
void loop() {
    // 1. Перевірка живлення через реле
    bool isPowerOn = digitalRead(RELAY_PIN) == HIGH;
    
    // 2. Вимірювання V/Hz (якщо PRO-сенсор)
    float voltage = readVoltage();
    float frequency = readFrequency();
    
    // 3. Відправка даних на сервер
    if (isPowerOn != lastPowerState) {
        sendDataToServer(isPowerOn, voltage, frequency);
        lastPowerState = isPowerOn;
    }
    
    // 4. Періодичний ping (кожні 60 сек)
    if (millis() - lastPingTime > 60000) {
        sendPing();
        lastPingTime = millis();
    }
    
    delay(10000); // 10 секунд
}

void sendDataToServer(bool powerOn, float v, float hz) {
    // POST /api/iot/data
    String payload = "{";
    payload += "\"sensor_id\": \"ESP32_" + String(SENSOR_ID) + "\",";
    payload += "\"is_power_on\": " + String(powerOn) + ",";
    payload += "\"voltage\": " + String(v) + ",";
    payload += "\"frequency\": " + String(hz);
    payload += "}";
    
    http.begin("https://api.svetlobot.ua/api/iot/data");
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", "Bearer " + String(API_KEY));
    http.POST(payload);
}
```

#### Backend Processing (iot_service.py)
```python
class IoTService:
    async def process_sensor_data(self, sensor_id: str, data: IoTData):
        # 1. Оновити статус сенсора
        await self.update_sensor_status(sensor_id, is_online=True)
        
        # 2. Зберегти дані
        await self.save_iot_data(sensor_id, data)
        
        # 3. Отримати чергу сенсора
        queue_id = await self.get_sensor_queue(sensor_id)
        
        # 4. Перевірити зміну стану
        current_state = await self.get_queue_state(queue_id)
        
        if data.is_power_on != current_state:
            # 5. Підтвердження від другого сенсора?
            other_sensor = await self.get_other_sensor(queue_id, sensor_id)
            other_data = await self.get_latest_data(other_sensor)
            
            if other_data and other_data.is_power_on == data.is_power_on:
                # ✅ Обидва сенсори підтверджують
                await self.update_queue_state(
                    queue_id, 
                    is_power_on=data.is_power_on,
                    source='iot'
                )
                
                # 6. Trigger notification
                await self.trigger_notification(
                    queue_id, 
                    'power_on' if data.is_power_on else 'power_off'
                )
```

---

### 5. **Система сповіщень**

#### Notification Dispatcher (Celery Task)
```python
@celery.task
async def send_notification(queue_id: int, notification_type: str):
    """
    Масова розсилка сповіщень для черги
    """
    # 1. Отримати користувачів черги
    users = await get_users_by_queue(queue_id)
    
    # 2. Фільтрація по тарифах
    eligible_users = []
    for user in users:
        if can_receive_notification(user, notification_type):
            eligible_users.append(user)
    
    # 3. Отримати текст з Excel
    message_template = await get_excel_text(f'{notification_type}_template')
    
    # 4. Відправка через батчі (1000 за раз)
    for batch in chunk(eligible_users, 1000):
        tasks = []
        for user in batch:
            message = message_template.format(
                queue=queue_id,
                time=datetime.now().strftime('%H:%M'),
                address=user.address
            )
            tasks.append(send_telegram_message(user.user_id, message))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 5. Rate limiting (30 msg/sec = Telegram limit)
        await asyncio.sleep(len(batch) / 30)
```

#### Warning Notifications (Schedule Checker)
```python
@celery_beat.task(run_every=timedelta(minutes=1))
async def check_schedules():
    """
    Перевірка графіків кожну хвилину
    """
    now = datetime.now()
    
    # Отримати графіки на сьогодні
    schedules = await get_today_schedules()
    
    for schedule in schedules:
        # Отримати користувачів черги з активними warning_times
        users = await get_users_with_warnings(schedule.queue_id)
        
        for user in users:
            for warning_time in user.settings['warning_times']:
                # Чи настав час відправки?
                target_time = schedule.start_time - timedelta(minutes=warning_time)
                
                if abs((target_time - now).total_seconds()) < 30:  # ±30 сек
                    # Перевірити, чи не відправляли вже
                    if not await was_notification_sent(user.user_id, schedule.id, warning_time):
                        await send_warning_notification(
                            user.user_id, 
                            schedule, 
                            warning_time
                        )
```

---

### 6. **Реферальна система**

#### Logic
```python
class ReferralService:
    async def activate_referral(self, referred_user_id: int, referrer_code: str):
        # 1. Знайти referrer
        referrer = await self.get_user_by_referral_code(referrer_code)
        
        if not referrer:
            raise ValueError("Невірний реферальний код")
        
        # 2. Перевірка (не може запросити себе)
        if referrer.user_id == referred_user_id:
            raise ValueError("Не можна використовувати свій код")
        
        # 3. Перевірка (чи вже використовував)
        if await self.is_referral_activated(referred_user_id):
            raise ValueError("Ви вже використали реферальний код")
        
        # 4. Нарахувати 5 днів referrer
        await self.grant_days(referrer.user_id, days=5, reason='referral')
        
        # 5. Зберегти зв'язок
        await self.save_referral_activation(referrer.user_id, referred_user_id)
        
        # 6. Оновити статистику
        await self.increment_referral_count(referrer.user_id)
        
        # 7. Повідомлення referrer
        await self.notify_referrer(referrer.user_id, referred_user_id)
        
        return {"success": True, "days_granted": 5}
```

---

### 7. **Excel-керування**

#### Parser
```python
class ExcelService:
    def __init__(self):
        self.addresses_file = 'data/addresses.xlsx'
        self.texts_file = 'data/texts.xlsx'
    
    async def load_addresses(self):
        """
        Структура addresses.xlsx:
        | Вулиця          | Будинок | Черга |
        |-----------------|---------|-------|
        | вул. Соборна    | 1       | 5     |
        | вул. Незалежності | 12   | 3     |
        """
        df = pd.read_excel(self.addresses_file)
        
        for _, row in df.iterrows():
            await db.addresses.upsert({
                'street': row['Вулиця'],
                'house_number': row['Будинок'],
                'queue_id': int(row['Черга'])
            })
    
    async def load_texts(self):
        """
        Структура texts.xlsx:
        | Ключ                  | Текст                          |
        |-----------------------|--------------------------------|
        | welcome_message       | Вітаємо у СвітлоБот!          |
        | power_off_template    | ⚡️ Відключення світла...     |
        """
        df = pd.read_excel(self.texts_file)
        
        for _, row in df.iterrows():
            await db.excel_texts.upsert({
                'key': row['Ключ'],
                'value': row['Текст']
            })
```

---

## МАСШТАБУВАННЯ

### Для 1,000,000 користувачів

#### 1. **Database Optimization**
```sql
-- Partitioning (notifications by month)
CREATE TABLE notifications_2025_01 PARTITION OF notifications
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Indexing
CREATE INDEX CONCURRENTLY idx_users_active 
ON users(last_active_at) WHERE is_blocked = FALSE;
```

#### 2. **Redis Caching**
```python
# Кеш статусу черг (TTL 10 сек)
await redis.setex(f'queue:{queue_id}:status', 10, 'ON')

# Кеш підписок (TTL 1 год)
await redis.setex(f'user:{user_id}:subscribed', 3600, 'true')
```

#### 3. **Celery Workers**
```yaml
# docker-compose.yml
celery_worker_1:
  command: celery -A tasks worker -Q notifications --concurrency=10

celery_worker_2:
  command: celery -A tasks worker -Q iot --concurrency=5
```

#### 4. **Horizontal Scaling**
```
Load Balancer (Nginx)
    ├── Backend 1 (FastAPI)
    ├── Backend 2 (FastAPI)
    └── Backend 3 (FastAPI)
```

---

## БЕЗПЕКА

### 1. **API Authentication**
```python
# Middleware для адмін-endpoints
async def verify_admin_token(request: Request):
    token = request.headers.get('X-Admin-Token')
    if token != settings.ADMIN_TOKEN:
        raise HTTPException(401, "Unauthorized")
```

### 2. **Rate Limiting**
```python
# Redis-based rate limiting (краудрепорти)
@ratelimit(key='user_id', rate='5/m')  # 5 на хвилину
async def send_crowdreport(user_id: int, data: CrowdReport):
    ...
```

### 3. **SQL Injection Prevention**
```python
# Використання ORM (SQLAlchemy)
result = await db.execute(
    select(Address).where(Address.street == street)
)
```

### 4. **Environment Variables**
```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost/svetlobot
REDIS_URL=redis://localhost:6379
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
LIQPAY_PUBLIC_KEY=sandbox_i12345678
LIQPAY_PRIVATE_KEY=sandbox_abcdefghijklmnopqrstuvwxyz1234567890
ADMIN_TOKEN=super_secret_admin_token_12345
```

---

## МОНІТОРИНГ

### 1. **Logs**
```python
# Structured logging
import structlog

logger = structlog.get_logger()

logger.info("notification_sent", 
    user_id=user_id, 
    queue_id=queue_id, 
    type=notification_type
)
```

### 2. **Alerts**
```python
# Алерти в адмін-бот
async def send_admin_alert(message: str):
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🚨 ALERT: {message}"
    )

# Приклади:
# - "Сенсор ESP32_005 offline >5 хв"
# - "Черга розсилки >10,000 повідомлень"
# - "База даних >80% CPU"
```

### 3. **Metrics**
```python
# Prometheus metrics (опціонально)
from prometheus_client import Counter, Histogram

notifications_sent = Counter('notifications_sent_total', 'Total notifications')
api_latency = Histogram('api_request_duration_seconds', 'API latency')
```

---

## DEPLOYMENT

### Docker Compose
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: svetlobot
      POSTGRES_USER: svetlobot_user
      POSTGRES_PASSWORD: strong_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    env_file:
      - .env

  bot:
    build: ./bot
    command: python main.py
    depends_on:
      - backend
    env_file:
      - .env

  celery_worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info
    depends_on:
      - postgres
      - redis
    env_file:
      - .env

  celery_beat:
    build: ./backend
    command: celery -A tasks beat --loglevel=info
    depends_on:
      - postgres
      - redis
    env_file:
      - .env

volumes:
  postgres_data:
  redis_data:
```

---

## ТЕХНОЛОГІЧНІ ВИМОГИ

### Backend
- Python 3.11+
- FastAPI 0.104+
- SQLAlchemy 2.0+
- Alembic (migrations)
- Pydantic (validation)

### Bot
- Aiogram 3.x
- Redis для FSM
- aiohttp для API calls

### Database
- PostgreSQL 14+
- Redis 7+

### IoT
- Arduino IDE
- ESP32 Board Manager
- TinyGSM library (для SIM7600)

### Deployment
- Docker 24+
- Docker Compose 2.x
- Ubuntu 22.04 LTS
- Nginx (reverse proxy)
- Certbot (SSL)

---

**Архітектура готова до імплементації! 🚀**