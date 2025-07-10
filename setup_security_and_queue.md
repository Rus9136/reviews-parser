# 🔐 Настройка безопасности и очереди уведомлений

## ✅ Выполненные улучшения

### 1. **Безопасность**
- ✅ Убраны все hardcoded токены и пароли из кода
- ✅ Настроено ограничение CORS для доверенных доменов
- ✅ Создан `.env.example` файл для разработчиков
- ✅ Добавлена валидация переменных окружения

### 2. **Очередь уведомлений**
- ✅ Установлен Redis для брокера сообщений
- ✅ Реализована очередь с Celery для Telegram уведомлений
- ✅ Настроен rate limiting (30 сообщений/сек)
- ✅ Добавлена retry логика с exponential backoff
- ✅ Создан systemd сервис для воркера очереди

### 3. **Кэширование**
- ✅ Добавлено кэширование часто запрашиваемых данных
- ✅ Настроены TTL для разных типов данных
- ✅ Реализована инвалидация кэша при обновлении данных
- ✅ Добавлены API endpoints для управления кэшем

---

## 🚀 Инструкции по установке и настройке

### Шаг 1: Обновление переменных окружения

Обновите ваш `.env` файл с новыми переменными:

```env
# Database configuration
DATABASE_URL=postgresql://reviews_user:reviews_password@localhost:5436/reviews_db

# API configuration
API_HOST=0.0.0.0
API_PORT=8004

# Parser configuration
PARSER_API_KEY=6e7e1929-4ea9-4a5d-8c05-d601860389bd
PARSER_BATCH_SIZE=50
PARSER_DELAY=1.0

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN=8109477829:AAFacevlPz4uJA9EH4ezOGBw9B3Rf5kl5xA

# Redis configuration (для очереди сообщений)
REDIS_URL=redis://localhost:6379

# CORS configuration
CORS_ALLOWED_ORIGINS=https://reviews.aqniet.site,https://another-trusted-domain.com
```

### Шаг 2: Установка новых зависимостей

```bash
# Активируем виртуальное окружение
source venv/bin/activate

# Устанавливаем новые зависимости
pip install redis>=5.0.0 celery>=5.3.0

# Или обновляем все зависимости
pip install -r requirements.txt
```

### Шаг 3: Запуск Redis

```bash
# Запуск Redis через Docker
docker-compose up -d reviews-redis

# Проверка работы Redis
redis-cli ping
# Должно вернуть: PONG
```

### Шаг 4: Настройка systemd сервиса для очереди

```bash
# Копируем файл сервиса
sudo cp telegram-queue.service /etc/systemd/system/

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable telegram-queue.service

# Запускаем сервис
sudo systemctl start telegram-queue.service

# Проверяем статус
sudo systemctl status telegram-queue.service
```

### Шаг 5: Перезапуск API сервиса

```bash
# Перезапускаем API для применения изменений
sudo systemctl restart reviews-api.service

# Проверяем статус
sudo systemctl status reviews-api.service
```

---

## 📋 Команды для управления

### Управление сервисами

```bash
# Статус всех сервисов
sudo systemctl status reviews-api.service
sudo systemctl status telegram-bot.service
sudo systemctl status telegram-queue.service

# Перезапуск сервисов
sudo systemctl restart reviews-api.service
sudo systemctl restart telegram-bot.service
sudo systemctl restart telegram-queue.service

# Просмотр логов
journalctl -u reviews-api.service -f
journalctl -u telegram-bot.service -f
journalctl -u telegram-queue.service -f
```

### Управление Redis

```bash
# Подключение к Redis
redis-cli

# Мониторинг Redis
redis-cli monitor

# Информация о Redis
redis-cli info memory
redis-cli info keyspace
```

### Управление очередью

```bash
# Запуск воркера очереди вручную (для тестирования)
cd /root/projects/reviews-parser
source venv/bin/activate
celery -A telegram_queue worker --loglevel=info --queues=telegram_notifications

# Мониторинг очереди
celery -A telegram_queue flower  # Веб-интерфейс на http://localhost:5555
```

### Управление кэшем

```bash
# Проверка статистики кэша
curl https://reviews.aqniet.site/api/v1/cache/stats

# Очистка всего кэша
curl -X POST https://reviews.aqniet.site/api/v1/cache/clear

# Очистка кэша для конкретного филиала
curl -X POST https://reviews.aqniet.site/api/v1/cache/clear/70000001067929337
```

---

## 🧪 Тестирование

### Проверка здоровья системы

```bash
# Проверка API и подключений
curl https://reviews.aqniet.site/health

# Ожидаемый ответ:
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "reviews_count": 18760,
  "branches_count": 23,
  "timestamp": "2025-07-10T12:00:00"
}
```

### Тестирование очереди уведомлений

```bash
# Тестирование системы уведомлений
cd /root/projects/reviews-parser
source venv/bin/activate
python telegram_notifications_queue.py
```

### Тестирование кэша

```bash
# Статистика кэша
curl https://reviews.aqniet.site/api/v1/cache/stats

# Тестирование API с кэшем
curl https://reviews.aqniet.site/api/v1/branches  # Первый запрос - из БД
curl https://reviews.aqniet.site/api/v1/branches  # Второй запрос - из кэша
```

---

## 🔧 Настройка мониторинга

### Логирование

Все компоненты логируют свою работу:

```bash
# Логи API
journalctl -u reviews-api.service -f

# Логи Telegram бота
journalctl -u telegram-bot.service -f

# Логи очереди уведомлений
journalctl -u telegram-queue.service -f

# Логи автоматического парсинга
tail -f logs/daily_parse_*.log
```

### Мониторинг производительности

```bash
# Мониторинг Redis
redis-cli --latency-history

# Мониторинг базы данных
docker exec reviews-db psql -U reviews_user -d reviews_db -c "SELECT * FROM pg_stat_activity;"

# Мониторинг очереди
celery -A telegram_queue inspect active
celery -A telegram_queue inspect reserved
```

---

## ⚠️ Важные замечания

### Безопасность
- ✅ Все токены теперь хранятся в переменных окружения
- ✅ CORS настроен только для доверенных доменов
- ✅ Файл `.env` НЕ должен попадать в git (убедитесь, что он в `.gitignore`)

### Производительность
- ✅ Кэш автоматически очищается при добавлении новых отзывов
- ✅ Очередь уведомлений соблюдает лимиты Telegram API
- ✅ Rate limiting настроен на 30 сообщений в секунду

### Отказоустойчивость
- ✅ Система работает даже при недоступности Redis
- ✅ Ошибки отправки уведомлений автоматически повторяются
- ✅ Все сервисы имеют restart=always в systemd

---

## 🎯 Следующие шаги

1. **Мониторинг (опционально)**
   - Настройка Prometheus для метрик
   - Настройка Grafana для визуализации
   - Алерты при сбоях

2. **Дополнительная безопасность**
   - Аутентификация для API
   - Rate limiting на уровне приложения
   - Шифрование данных в Redis

3. **Оптимизация**
   - Настройка Redis clustering
   - Горизонтальное масштабирование Celery
   - Оптимизация запросов к БД

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте статус всех сервисов
2. Просмотрите логи systemd
3. Убедитесь, что Redis доступен
4. Проверьте переменные окружения
5. Обратитесь к этому документу для решения типичных проблем

**Система готова к производственному использованию!** 🚀