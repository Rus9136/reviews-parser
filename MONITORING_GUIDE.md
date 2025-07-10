# 📊 Руководство по мониторингу системы Reviews Parser

---

## 🎯 Основные метрики для мониторинга

### 1. **API Сервис** (`reviews-api.service`)
```bash
# Статус сервиса
systemctl status reviews-api.service

# Логи в реальном времени
journalctl -u reviews-api.service -f

# Проверка доступности
curl http://127.0.0.1:8004/health | jq
```

**Ключевые метрики:**
- Статус: `active (running)`
- Время ответа API: < 100ms
- Подключения к БД и кэшу: `connected`

### 2. **Telegram Queue** (`telegram-queue.service`)
```bash
# Статус воркера очереди
systemctl status telegram-queue.service

# Логи воркера
journalctl -u telegram-queue.service -f

# Статистика очереди
curl http://127.0.0.1:8004/api/v1/cache/stats | jq
```

**Ключевые метрики:**
- Активные задачи: обычно 0-5
- Зарезервированные задачи: < 100
- Время обработки: < 1 секунды на задачу

### 3. **Redis** (кэш и очередь)
```bash
# Проверка доступности
docker exec reviews-redis redis-cli ping

# Информация о памяти
docker exec reviews-redis redis-cli info memory

# Количество ключей
docker exec reviews-redis redis-cli info keyspace

# Статистика через API
curl http://127.0.0.1:8004/api/v1/cache/stats | jq
```

**Ключевые метрики:**
- Память: < 100MB (обычно 1-5MB)
- Ключи: 0-50 (зависит от нагрузки)
- Hit ratio: > 80%

### 4. **PostgreSQL**
```bash
# Статус контейнера
docker ps | grep reviews-db

# Подключение к БД
docker exec -it reviews-db psql -U reviews_user -d reviews_db

# Размер БД
docker exec reviews-db psql -U reviews_user -d reviews_db -c "
  SELECT pg_size_pretty(pg_database_size('reviews_db'));"

# Активные соединения
docker exec reviews-db psql -U reviews_user -d reviews_db -c "
  SELECT count(*) FROM pg_stat_activity;"
```

**Ключевые метрики:**
- Размер БД: зависит от количества отзывов
- Активные соединения: < 20
- Время ответа: < 50ms

---

## 🚨 Алерты и пороговые значения

### Критические алерты:
- **API недоступен**: HTTP код != 200
- **БД недоступна**: `database != "connected"`
- **Воркер очереди остановлен**: `systemctl is-active != "active"`

### Предупреждения:
- **Redis недоступен**: `cache != "connected"`
- **Высокая нагрузка**: время ответа > 500ms
- **Переполнение очереди**: > 1000 задач в очереди

### Информационные:
- **Новые отзывы**: количество увеличилось
- **Перезапуск сервисов**: изменился uptime
- **Использование памяти**: Redis > 50MB

---

## 📈 Команды для ежедневного мониторинга

### Быстрая проверка системы:
```bash
#!/bin/bash
# quick_health_check.sh

echo "🏥 ПРОВЕРКА ЗДОРОВЬЯ СИСТЕМЫ"
echo "=============================="

# API Health
echo "📡 API:"
curl -s http://127.0.0.1:8004/health | jq -r '"  Status: " + .status + " | DB: " + .database + " | Cache: " + .cache'

# Services
echo "🔧 Сервисы:"
echo "  API: $(systemctl is-active reviews-api.service)"
echo "  Telegram Bot: $(systemctl is-active telegram-bot.service)"
echo "  Telegram Queue: $(systemctl is-active telegram-queue.service)"

# Docker containers
echo "🐳 Контейнеры:"
echo "  Redis: $(docker inspect -f '{{.State.Status}}' reviews-redis 2>/dev/null || echo 'stopped')"
echo "  PostgreSQL: $(docker inspect -f '{{.State.Status}}' reviews-db 2>/dev/null || echo 'stopped')"

# Disk space
echo "💾 Место на диске:"
df -h / | tail -1 | awk '{print "  Использовано: " $5 " (" $3 "/" $2 ")"}'

echo "=============================="
echo "✅ Проверка завершена"
```

### Детальная диагностика:
```bash
#!/bin/bash
# detailed_diagnostics.sh

echo "🔬 ДЕТАЛЬНАЯ ДИАГНОСТИКА"
echo "========================"

# API performance
echo "⚡ Производительность API:"
time curl -s http://127.0.0.1:8004/api/v1/branches > /dev/null

# Cache stats
echo "💾 Статистика кэша:"
curl -s http://127.0.0.1:8004/api/v1/cache/stats | jq

# Queue stats
echo "📬 Статистика очереди:"
journalctl -u telegram-queue.service --since "1 hour ago" | grep -c "succeeded"

# Database stats
echo "🗃️  Статистика БД:"
docker exec reviews-db psql -U reviews_user -d reviews_db -c "
  SELECT 'Reviews: ' || count(*) FROM reviews;
  SELECT 'Branches: ' || count(*) FROM branches;
  SELECT 'Parse Reports: ' || count(*) FROM parse_reports;"

# Recent errors
echo "❌ Последние ошибки:"
journalctl --since "1 hour ago" --priority=err | tail -5

echo "========================"
echo "✅ Диагностика завершена"
```

---

## 🔧 Автоматизация мониторинга

### Создание cron задач для мониторинга:
```bash
# Добавить в crontab
crontab -e

# Проверка каждые 5 минут
*/5 * * * * /root/projects/reviews-parser/quick_health_check.sh >> /var/log/reviews-health.log 2>&1

# Детальная проверка каждый час
0 * * * * /root/projects/reviews-parser/detailed_diagnostics.sh >> /var/log/reviews-diagnostics.log 2>&1

# Очистка старых логов каждый день
0 2 * * * find /root/projects/reviews-parser/logs -name "*.log" -mtime +7 -delete
```

### Уведомления при сбоях:
```bash
#!/bin/bash
# alert_on_failure.sh

API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8004/health)

if [ "$API_STATUS" != "200" ]; then
    echo "🚨 АЛЕРТ: API недоступен (код: $API_STATUS)" | \
    mail -s "Reviews Parser Alert" admin@example.com
fi

# Проверка сервисов
for SERVICE in reviews-api telegram-bot telegram-queue; do
    if ! systemctl is-active --quiet $SERVICE.service; then
        echo "🚨 АЛЕРТ: Сервис $SERVICE остановлен" | \
        mail -s "Reviews Parser Alert" admin@example.com
    fi
done
```

---

## 📊 Логи и их местоположение

### Системные логи:
```bash
# API сервис
journalctl -u reviews-api.service

# Telegram Bot
journalctl -u telegram-bot.service

# Telegram Queue
journalctl -u telegram-queue.service

# Системные ошибки
journalctl --priority=err --since "1 day ago"
```

### Логи приложений:
```bash
# Автоматический парсинг
tail -f /root/projects/reviews-parser/logs/daily_parse_*.log

# Cron задачи
tail -f /root/projects/reviews-parser/logs/cron.log

# Nginx (если используется)
docker logs hr-nginx --tail 100
```

### Логи Docker:
```bash
# Redis
docker logs reviews-redis --tail 100

# PostgreSQL
docker logs reviews-db --tail 100
```

---

## 🔍 Поиск и анализ проблем

### Частые проблемы и решения:

#### 1. **API возвращает 503**
```bash
# Проверить БД
docker ps | grep reviews-db
curl http://127.0.0.1:8004/health | jq .database

# Решение
docker start reviews-db
```

#### 2. **Медленные запросы**
```bash
# Проверить кэш
curl http://127.0.0.1:8004/health | jq .cache

# Очистить кэш
curl -X POST http://127.0.0.1:8004/api/v1/cache/clear
```

#### 3. **Уведомления не отправляются**
```bash
# Проверить воркер очереди
systemctl status telegram-queue.service

# Проверить Redis
docker exec reviews-redis redis-cli ping

# Решение
systemctl restart telegram-queue.service
```

#### 4. **Высокое использование памяти**
```bash
# Проверить Redis
docker exec reviews-redis redis-cli info memory

# Очистить кэш
curl -X POST http://127.0.0.1:8004/api/v1/cache/clear

# Перезапустить Redis
docker restart reviews-redis
```

---

## 📱 Мониторинг через Telegram (опционально)

### Создание бота для мониторинга:
```python
# monitoring_bot.py
import requests
import schedule
import time

def check_system_health():
    try:
        response = requests.get('http://127.0.0.1:8004/health', timeout=5)
        if response.status_code != 200:
            send_alert("🚨 API недоступен!")
    except:
        send_alert("🚨 API не отвечает!")

def send_alert(message):
    # Отправка в Telegram или другой мессенджер
    pass

# Проверка каждые 5 минут
schedule.every(5).minutes.do(check_system_health)

while True:
    schedule.run_pending()
    time.sleep(1)
```

---

## 📋 Чек-лист ежедневных проверок

### Утренняя проверка:
- [ ] Все сервисы запущены
- [ ] API отвечает на `/health`
- [ ] БД и кэш подключены
- [ ] Новые отзывы парсятся
- [ ] Уведомления отправляются

### Еженедельная проверка:
- [ ] Размер логов < 1GB
- [ ] Место на диске > 20%
- [ ] Нет критических ошибок в логах
- [ ] Производительность API < 100ms
- [ ] Обновления безопасности

### Ежемесячная проверка:
- [ ] Backup базы данных
- [ ] Обновление SSL сертификатов
- [ ] Анализ метрик производительности
- [ ] Планирование масштабирования

---

**Создано:** 2025-07-10  
**Версия:** 1.0  
**Следующее обновление:** При изменении архитектуры