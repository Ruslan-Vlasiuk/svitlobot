# DEPLOYMENT GUIDE: СвітлоБот

**Version:** 1.0  
**Date:** 2025-11-08  
**Target Platform:** VPS Ubuntu 22.04, Docker

---

## ЗМІСТ

1. [Вимоги до сервера](#вимоги-до-сервера)
2. [Підготовка VPS](#підготовка-vps)
3. [Встановлення Docker](#встановлення-docker)
4. [Клонування проекту](#клонування-проекту)
5. [Налаштування .env](#налаштування-env)
6. [Запуск проекту](#запуск-проекту)
7. [Ініціалізація бази даних](#ініціалізація-бази-даних)
8. [Завантаження Excel-даних](#завантаження-excel-даних)
9. [Налаштування Nginx](#налаштування-nginx)
10. [SSL сертифікат](#ssl-сертифікат)
11. [Моніторинг та логи](#моніторинг-та-логи)
12. [Backup](#backup)
13. [Оновлення проекту](#оновлення-проекту)
14. [Troubleshooting](#troubleshooting)

---

## ВИМОГИ ДО СЕРВЕРА

### Мінімальні (для тестування)
- **CPU:** 2 cores
- **RAM:** 4 GB
- **Storage:** 40 GB SSD
- **OS:** Ubuntu 22.04 LTS
- **Bandwidth:** 100 Mbps

### Рекомендовані (для 1M користувачів)
- **CPU:** 8 cores
- **RAM:** 16 GB
- **Storage:** 200 GB SSD
- **OS:** Ubuntu 22.04 LTS
- **Bandwidth:** 1 Gbps

### Провайдери
- **Ukraine:** Hetzner (Falkenstein), DigitalOcean (Amsterdam)
- **Альтернативи:** AWS EC2, Google Cloud, Azure

---

## ПІДГОТОВКА VPS

### 1. Підключення до сервера
```bash
ssh root@your_server_ip
```

### 2. Оновлення системи
```bash
apt update && apt upgrade -y
```

### 3. Встановлення необхідних пакетів
```bash
apt install -y \
    git \
    curl \
    wget \
    htop \
    nano \
    ufw \
    fail2ban \
    python3-pip
```

### 4. Налаштування firewall (UFW)
```bash
# Дозволити SSH
ufw allow 22/tcp

# Дозволити HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Увімкнути firewall
ufw enable
```

### 5. Створення користувача (опціонально)
```bash
adduser svetlobot
usermod -aG sudo svetlobot
su - svetlobot
```

---

## ВСТАНОВЛЕННЯ DOCKER

### 1. Видалити старі версії (якщо є)
```bash
sudo apt remove docker docker-engine docker.io containerd runc
```

### 2. Встановити Docker
```bash
# Додати Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Додати репозиторій
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Встановити Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 3. Додати користувача до групи docker
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 4. Перевірити встановлення
```bash
docker --version
docker compose version
```

---

## КЛОНУВАННЯ ПРОЕКТУ

### 1. Створити директорію проекту
```bash
mkdir -p ~/projects
cd ~/projects
```

### 2. Клонувати репозиторій (якщо є Git)
```bash
git clone https://github.com/yourusername/svetlobot.git
cd svetlobot
```

**АБО** завантажити файли вручну:
```bash
# Створити структуру
mkdir -p svetlobot/{backend,bot,admin_bot,iot,data}
cd svetlobot
```

---

## НАЛАШТУВАННЯ .ENV

### 1. Створити .env файл
```bash
nano .env
```

### 2. Заповнити змінні
```bash
# ============================================
# ЗАГАЛЬНІ НАЛАШТУВАННЯ
# ============================================
ENVIRONMENT=production
DEBUG=false
TIMEZONE=Europe/Kiev

# ============================================
# БАЗА ДАНИХ (PostgreSQL)
# ============================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=svetlobot
POSTGRES_USER=svetlobot_user
POSTGRES_PASSWORD=ЗАМІНІТЬ_НА_СКЛАДНИЙ_ПАРОЛЬ_123456

DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# ============================================
# REDIS
# ============================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=ЗАМІНІТЬ_НА_СКЛАДНИЙ_ПАРОЛЬ_789012
REDIS_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0

# ============================================
# TELEGRAM
# ============================================
# Основний бот
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456

# Адмін-бот
ADMIN_BOT_TOKEN=9876543210:ZYXwvuTSRqponMLKjihGFEdcba987654

# Канал
TELEGRAM_CHANNEL_ID=-1001234567890
TELEGRAM_CHANNEL_USERNAME=@svetlo_irpin

# Адміністратори (через кому)
ADMIN_USER_IDS=123456789,987654321

# ============================================
# BACKEND API
# ============================================
API_HOST=0.0.0.0
API_PORT=8000
API_BASE_URL=https://api.svetlobot.ua

# Токен для адмін-endpoints
ADMIN_API_TOKEN=ЗАМІНІТЬ_НА_СКЛАДНИЙ_ТОКЕН_ABC123XYZ

# ============================================
# ПЛАТЕЖІ (LiqPay)
# ============================================
LIQPAY_PUBLIC_KEY=sandbox_i12345678
LIQPAY_PRIVATE_KEY=sandbox_abcdefghijklmnopqrstuvwxyz1234567890
LIQPAY_CALLBACK_URL=https://api.svetlobot.ua/api/payments/callback

# Ціни (в UAH)
STANDARD_PRICE_1M=50
STANDARD_PRICE_3M=130
STANDARD_PRICE_6M=230
PRO_PRICE_1M=100
PRO_PRICE_3M=260
PRO_PRICE_6M=460

# ============================================
# IoT
# ============================================
IOT_API_KEY=ЗАМІНІТЬ_НА_СКЛАДНИЙ_КЛЮЧ_IoT_XYZ789

# ============================================
# CELERY
# ============================================
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# ============================================
# ЛОГУВАННЯ
# ============================================
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=10

# ============================================
# МАСШТАБУВАННЯ
# ============================================
CELERY_WORKERS=5
MAX_NOTIFICATION_RATE=30  # повідомлень/сек (Telegram limit)
```

### 3. Зберегти файл
```bash
# Ctrl+O → Enter → Ctrl+X
```

### 4. Встановити права
```bash
chmod 600 .env
```

---

## ЗАПУСК ПРОЕКТУ

### 1. Створити docker-compose.yml
```bash
nano docker-compose.yml
```

```yaml
version: '3.8'

services:
  # ==========================================
  # POSTGRES
  # ==========================================
  postgres:
    image: postgres:14-alpine
    container_name: svetlobot_postgres
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - svetlobot_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==========================================
  # REDIS
  # ==========================================
  redis:
    image: redis:7-alpine
    container_name: svetlobot_redis
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - svetlobot_network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==========================================
  # BACKEND API
  # ==========================================
  backend:
    build: ./backend
    container_name: svetlobot_backend
    restart: always
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./backend:/app
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - svetlobot_network

  # ==========================================
  # TELEGRAM BOT
  # ==========================================
  bot:
    build: ./bot
    container_name: svetlobot_bot
    restart: always
    command: python main.py
    env_file:
      - .env
    volumes:
      - ./bot:/app
      - ./data:/app/data
    depends_on:
      - backend
    networks:
      - svetlobot_network

  # ==========================================
  # ADMIN BOT
  # ==========================================
  admin_bot:
    build: ./admin_bot
    container_name: svetlobot_admin_bot
    restart: always
    command: python main.py
    env_file:
      - .env
    volumes:
      - ./admin_bot:/app
    depends_on:
      - backend
    networks:
      - svetlobot_network

  # ==========================================
  # CELERY WORKER (notifications)
  # ==========================================
  celery_worker_notifications:
    build: ./backend
    container_name: svetlobot_celery_notifications
    restart: always
    command: celery -A tasks worker -Q notifications --loglevel=info --concurrency=10
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    networks:
      - svetlobot_network

  # ==========================================
  # CELERY WORKER (iot)
  # ==========================================
  celery_worker_iot:
    build: ./backend
    container_name: svetlobot_celery_iot
    restart: always
    command: celery -A tasks worker -Q iot --loglevel=info --concurrency=5
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    networks:
      - svetlobot_network

  # ==========================================
  # CELERY BEAT (scheduler)
  # ==========================================
  celery_beat:
    build: ./backend
    container_name: svetlobot_celery_beat
    restart: always
    command: celery -A tasks beat --loglevel=info
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    networks:
      - svetlobot_network

networks:
  svetlobot_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
```

### 2. Запустити проект
```bash
docker compose up -d
```

### 3. Перевірити статус
```bash
docker compose ps
```

Має бути:
```
NAME                        STATUS
svetlobot_postgres          Up (healthy)
svetlobot_redis             Up (healthy)
svetlobot_backend           Up
svetlobot_bot               Up
svetlobot_admin_bot         Up
svetlobot_celery_notifications  Up
svetlobot_celery_iot        Up
svetlobot_celery_beat       Up
```

---

## ІНІЦІАЛІЗАЦІЯ БАЗИ ДАНИХ

### 1. Виконати міграції
```bash
docker compose exec backend alembic upgrade head
```

### 2. Створити початкові черги
```bash
docker compose exec backend python -c "
from database import SessionLocal
from models import Queue

db = SessionLocal()
for i in range(1, 13):
    queue = Queue(queue_id=i, name=f'Черга {i}', is_power_on=True)
    db.merge(queue)
db.commit()
print('✅ Створено 12 черг')
"
```

---

## ЗАВАНТАЖЕННЯ EXCEL-ДАНИХ

### 1. Підготувати Excel-файли

**addresses.xlsx:**
```
| Вулиця          | Будинок | Черга |
|-----------------|---------|-------|
| вул. Соборна    | 1       | 5     |
| вул. Незалежності | 12   | 3     |
| пров. Мирний    | 7А      | 8     |
```

**texts.xlsx:**
```
| Ключ                  | Текст                                |
|-----------------------|--------------------------------------|
| welcome_message       | 👋 Вітаємо у СвітлоБот!             |
| power_off_template    | ⚡️ Відключення світла\n📍 Черга: {queue}\n🕒 Час: {time} |
| power_on_template     | ✅ Світло увімкнено\n📍 Черга: {queue}\n🕒 Час: {time}  |
```

### 2. Завантажити файли на сервер
```bash
# З локальної машини
scp addresses.xlsx root@your_server_ip:~/projects/svetlobot/data/
scp texts.xlsx root@your_server_ip:~/projects/svetlobot/data/
```

### 3. Імпортувати дані
```bash
docker compose exec backend python -c "
from services.excel_service import ExcelService

excel = ExcelService()
excel.load_addresses()
excel.load_texts()
print('✅ Excel-дані завантажено')
"
```

---

## НАЛАШТУВАННЯ NGINX

### 1. Встановити Nginx
```bash
sudo apt install -y nginx
```

### 2. Створити конфіг
```bash
sudo nano /etc/nginx/sites-available/svetlobot
```

```nginx
server {
    listen 80;
    server_name api.svetlobot.ua;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Активувати конфіг
```bash
sudo ln -s /etc/nginx/sites-available/svetlobot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## SSL СЕРТИФІКАТ

### 1. Встановити Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Отримати сертифікат
```bash
sudo certbot --nginx -d api.svetlobot.ua
```

### 3. Автоматичне оновлення
```bash
sudo crontab -e
```
Додати:
```
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## МОНІТОРИНГ ТА ЛОГИ

### 1. Переглянути логи
```bash
# Всі контейнери
docker compose logs -f

# Конкретний сервіс
docker compose logs -f bot

# Останні 100 рядків
docker compose logs --tail=100 backend
```

### 2. Моніторинг ресурсів
```bash
# Статистика контейнерів
docker stats

# Системні ресурси
htop
```

### 3. Перевірка бази даних
```bash
# Підключитися до PostgreSQL
docker compose exec postgres psql -U svetlobot_user -d svetlobot

# Команди:
\dt                    # Список таблиць
SELECT COUNT(*) FROM users;
SELECT * FROM queues;
\q                     # Вийти
```

---

## BACKUP

### 1. Backup бази даних
```bash
# Створити backup
docker compose exec postgres pg_dump -U svetlobot_user svetlobot > backup_$(date +%Y%m%d).sql

# Або автоматично щодня
crontab -e
```
Додати:
```bash
0 3 * * * cd ~/projects/svetlobot && docker compose exec -T postgres pg_dump -U svetlobot_user svetlobot > backups/backup_$(date +\%Y\%m\%d).sql
```

### 2. Відновлення
```bash
# З backup файлу
docker compose exec -T postgres psql -U svetlobot_user svetlobot < backup_20251108.sql
```

### 3. Backup .env та data
```bash
# Створити архів
tar -czf svetlobot_backup_$(date +%Y%m%d).tar.gz .env data/
```

---

## ОНОВЛЕННЯ ПРОЕКТУ

### 1. Стандартне оновлення
```bash
# Зупинити проект
docker compose down

# Оновити код (якщо Git)
git pull origin main

# Перебудувати образи
docker compose build

# Запустити
docker compose up -d

# Міграції (якщо є)
docker compose exec backend alembic upgrade head
```

### 2. Оновлення без downtime (Zero Downtime)
```bash
# 1. Запустити нові контейнери
docker compose up -d --scale bot=2 --scale backend=2 --no-recreate

# 2. Зачекати 10 сек
sleep 10

# 3. Зупинити старі
docker compose stop bot backend

# 4. Видалити старі
docker compose rm -f bot backend

# 5. Масштабувати назад
docker compose up -d --scale bot=1 --scale backend=1
```

---

## TROUBLESHOOTING

### Проблема: Бот не відповідає
```bash
# 1. Перевірити статус
docker compose ps bot

# 2. Логи
docker compose logs --tail=50 bot

# 3. Перезапустити
docker compose restart bot
```

### Проблема: База даних не підключається
```bash
# 1. Перевірити контейнер
docker compose ps postgres

# 2. Тестове підключення
docker compose exec postgres pg_isready -U svetlobot_user

# 3. Перезапустити
docker compose restart postgres
```

### Проблема: Сповіщення не відправляються
```bash
# 1. Перевірити Celery workers
docker compose logs celery_worker_notifications

# 2. Перевірити чергу в Redis
docker compose exec redis redis-cli -a $REDIS_PASSWORD
> LLEN celery

# 3. Перезапустити workers
docker compose restart celery_worker_notifications celery_beat
```

### Проблема: Диск заповнений
```bash
# 1. Перевірити розмір
df -h

# 2. Видалити старі логи
docker compose exec backend find /var/log -name "*.log" -mtime +10 -delete

# 3. Видалити старі образи
docker system prune -a
```

### Проблема: IoT-сенсори не надсилають дані
```bash
# 1. Перевірити endpoint
curl -X POST https://api.svetlobot.ua/api/iot/data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $IOT_API_KEY" \
  -d '{"sensor_id":"ESP32_001","is_power_on":true}'

# 2. Логи IoT worker
docker compose logs celery_worker_iot

# 3. Перевірити таблицю
docker compose exec postgres psql -U svetlobot_user -d svetlobot -c \
  "SELECT * FROM iot_sensors ORDER BY last_ping_at DESC LIMIT 10;"
```

---

## КОРИСНІ КОМАНДИ

### Docker
```bash
# Зупинити всі контейнери
docker compose down

# Зупинити + видалити volumes (УВАГА: видалить БД!)
docker compose down -v

# Переглянути використання диску
docker system df

# Очистити все
docker system prune -a --volumes
```

### PostgreSQL
```bash
# Експорт даних
docker compose exec postgres pg_dump -U svetlobot_user svetlobot -t users > users.sql

# Імпорт даних
docker compose exec -T postgres psql -U svetlobot_user svetlobot < users.sql

# Вакуум (оптимізація)
docker compose exec postgres psql -U svetlobot_user -d svetlobot -c "VACUUM ANALYZE;"
```

### Redis
```bash
# Підключитися
docker compose exec redis redis-cli -a $REDIS_PASSWORD

# Очистити кеш
docker compose exec redis redis-cli -a $REDIS_PASSWORD FLUSHALL
```

---

## CHECKLIST ПЕРЕД ЗАПУСКОМ

- [ ] VPS створено (Ubuntu 22.04)
- [ ] Docker та Docker Compose встановлено
- [ ] Проект склоновано/завантажено
- [ ] .env файл налаштовано (всі паролі змінено!)
- [ ] docker-compose.yml створено
- [ ] Firewall налаштовано (UFW)
- [ ] Nginx встановлено та налаштовано
- [ ] SSL сертифікат отримано (Certbot)
- [ ] `docker compose up -d` виконано успішно
- [ ] Міграції виконано (`alembic upgrade head`)
- [ ] Черги створено (1-12)
- [ ] Excel-файли завантажено (addresses.xlsx, texts.xlsx)
- [ ] Telegram-бот відповідає на /start
- [ ] API доступний (https://api.svetlobot.ua/docs)
- [ ] Backup налаштовано (cron)
- [ ] Моніторинг працює (логи, алерти)

---

**Проект розгорнуто! 🚀**