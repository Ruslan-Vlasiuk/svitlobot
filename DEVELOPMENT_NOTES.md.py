# DEVELOPMENT NOTES: Быстрые заметки

Этот файл для записи быстрых заметок, которые не вошли в основную документацию.

---

## 🔥 КРИТИЧЕСКИ ВАЖНО

### Перед деплоем на VPS:
- [ ] Сменить ВСЕ пароли в .env на продакшн версии
- [ ] НИКОГДА не коммитить .env в git
- [ ] Создать отдельный .env.production

### Telegram токены (ПОЛУЧИТЬ ДО ШАГА 5):
```bash
# 1. Создать основного бота
/start → @BotFather → /newbot → название → username

# 2. Создать админ-бота
/start → @BotFather → /newbot → название_admin → username_admin

# 3. Создать канал
Telegram → New Channel → @svetlo_irpin

# 4. Получить channel_id
@getidsbot → Forward message from channel
```

---

## 💾 BACKUP ВАЖНЫХ ДАННЫХ

### Локальная разработка:
```bash
# Backup БД
docker-compose exec postgres pg_dump -U svetlobot_user svetlobot > backup_$(date +%Y%m%d).sql

# Восстановление
docker-compose exec -T postgres psql -U svetlobot_user svetlobot < backup_20251109.sql
```

---

## 🐞 ЧАСТЫЕ ОШИБКИ

### 1. "Module not found"
```bash
# Решение: Пересобрать backend
docker-compose build backend
docker-compose up -d backend
```

### 2. "Connection refused" к PostgreSQL
```bash
# Решение: Проверить что контейнер запущен
docker-compose ps
docker-compose up -d postgres
```

### 3. Alembic не видит изменения
```bash
# Решение: Проверить что модель импортирована в alembic/env.py
# И что таблица есть в Base.metadata
```

---

## 📝 БЫСТРЫЕ ЗАМЕТКИ

### 2025-11-09:
- Docker Desktop не работает на macOS 13 → используем Colima
- `docker-compose` с дефисом (не `docker compose`)
- Alembic требует явный импорт моделей
- psycopg2-binary нужен для Alembic

---

## 🎯 СЛЕДУЮЩИЕ ШАГИ (КРАТКАЯ ВЕРСИЯ)

### День 2 (Завтра):
1. API Endpoints (users, queues, addresses, notifications, iot)
2. Начать Telegram Bot

### День 3:
3. Telegram Bot (handlers, keyboards, FSM)
4. Notification System (Celery)
5. Payments (LiqPay)

### Перед продакшн:
- Получить Telegram токены
- Купить VPS на Vultr
- Настроить домен и SSL
- Сменить все пароли
- Настроить автоматический backup

---

## 🔗 ПОЛЕЗНЫЕ ССЫЛКИ (БЫСТРЫЙ ДОСТУП)

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- PostgreSQL GUI: pgAdmin / DBeaver (если нужно)

---

_Добавляй сюда всё что приходит в голову во время разработки!_