# CLAUDE.md - Reviews Parser API Documentation

## 🎯 Назначение проекта

Этот проект предназначен для парсинга отзывов с платформы 2GIS для сети точек продаж "Сандык Тары" и предоставления API для доступа к собранным данным.

## 🏗️ Архитектура

### Компоненты системы:

1. **Parser** (`parser.py`)
   - Класс `TwoGISReviewsParser` для парсинга отзывов через публичное API 2GIS
   - Поддержка пагинации и batch-обработки
   - Извлечение фотографий из отзывов
   - Сохранение в CSV и JSON форматы

2. **Database** (`database.py`)
   - PostgreSQL база данных на порту 5436
   - SQLAlchemy ORM модели
   - Три таблицы: branches, reviews, parse_reports
   - Поддержка JSON для хранения фотографий
   - Индексы для оптимизации запросов

3. **API** (`api_v2.py`)
   - FastAPI приложение на порту 8004
   - RESTful endpoints для доступа к данным
   - Поддержка фотографий в API ответах
   - Swagger документация
   - CORS поддержка

4. **Migration** (`migrate_to_db.py`)
   - Скрипт для миграции данных из CSV/JSON в PostgreSQL
   - Обработка различных форматов дат
   - Создание отчетов о миграции

5. **Автоматический парсинг** (`daily_parse.py`)
   - Инкрементальный парсинг новых отзывов
   - Автоматический запуск через cron (ежедневно в 3:00)
   - Детальное логирование процесса
   - Создание отчетов в БД

## 🌐 Развертывание

### Домен
- **Production URL**: https://reviews.aqniet.site
- **SSL**: Let's Encrypt (до 2025-10-07)
- **Nginx**: Reverse proxy в host network mode

### Инфраструктура
- **База данных**: PostgreSQL 15 в Docker контейнере
- **API сервер**: Python 3.11 + FastAPI + uvicorn
- **Systemd**: reviews-api.service для автозапуска
- **Nginx**: Конфигурация в `/root/projects/hr-miniapp/nginx.conf`

### Порты
- **8004** - API сервер
- **5436** - PostgreSQL база данных

## 📊 API Endpoints

### Основные маршруты
- `GET /` - Информация об API
- `GET /health` - Проверка состояния системы
- `GET /docs` - Swagger UI документация
- `GET /redoc` - ReDoc документация

### API v1
- `GET /api/v1/branches` - Список всех филиалов
- `GET /api/v1/branches/{branch_id}/stats` - Статистика филиала
- `GET /api/v1/reviews` - Отзывы с фильтрацией
- `GET /api/v1/reviews/{review_id}` - Конкретный отзыв
- `GET /api/v1/stats` - Общая статистика
- `GET /api/v1/stats/recent` - Недавняя активность

### Параметры фильтрации
- `branch_id` - ID филиала
- `branch_name` - Название филиала
- `rating` - Рейтинг (1-5)
- `verified_only` - Только подтвержденные
- `date_from/date_to` - Диапазон дат
- `search` - Поиск по тексту
- `sort_by` - Сортировка
- `order` - Порядок (asc/desc)
- `skip/limit` - Пагинация

### Поля ответа с фотографиями
Каждый отзыв теперь содержит:
- `photos_count` - количество фотографий
- `photos_urls` - массив URL фотографий

## 🔧 Конфигурация

### Environment Variables (.env)
```env
DATABASE_URL=postgresql://reviews_user:reviews_password@localhost:5436/reviews_db
API_HOST=0.0.0.0
API_PORT=8004
PARSER_API_KEY=6e7e1929-4ea9-4a5d-8c05-d601860389bd
```

### Nginx Configuration
⚠️ **ВАЖНО**: Nginx работает в host network mode, поэтому все upstream-ы должны использовать `127.0.0.1` вместо имен контейнеров:
```nginx
proxy_pass http://127.0.0.1:8004;  # НЕ http://reviews-api:8004
```

## 🚀 Команды управления

### Запуск/остановка сервиса
```bash
systemctl start reviews-api.service
systemctl stop reviews-api.service
systemctl restart reviews-api.service
systemctl status reviews-api.service
```

### Просмотр логов
```bash
journalctl -u reviews-api.service -f
```

### База данных
```bash
# Подключение к БД
docker exec -it reviews-db psql -U reviews_user -d reviews_db

# Backup
docker exec reviews-db pg_dump -U reviews_user reviews_db > backup.sql

# Restore
docker exec -i reviews-db psql -U reviews_user reviews_db < backup.sql
```

### Автоматический парсинг
```bash
# Настройка автоматического парсинга (один раз)
./setup_cron.sh

# Ручной запуск инкрементального парсинга
source venv/bin/activate
python daily_parse.py

# Просмотр логов автоматического парсинга
tail -f logs/cron.log
tail -f logs/daily_parse_*.log
```

### Управление cron заданиями
```bash
crontab -l                    # Просмотр текущих заданий
crontab -e                    # Редактирование
./run_daily_parse.sh          # Ручной запуск через wrapper
```

## 🔍 Отладка

### Проверка здоровья API
```bash
curl https://reviews.aqniet.site/health
```

### Тестирование локально
```bash
curl http://127.0.0.1:8004/health
```

### Проблемы с 502 Bad Gateway
1. Проверить статус сервиса: `systemctl status reviews-api.service`
2. Проверить порт: `netstat -tlnp | grep 8004`
3. Проверить firewall: `ufw status`
4. Проверить nginx logs: `docker logs hr-nginx`

## 📊 Текущая статистика системы

- **Общее количество отзывов**: 18,753
- **Отзывов с фотографиями**: 2,642 (14.1%)
- **Активных филиалов**: 20 из 23
- **Автоматический парсинг**: ✅ Настроен (ежедневно в 3:00)
- **Последнее обновление**: 2025-07-09

## 📋 TODO / Улучшения

1. **Мониторинг**
   - Интеграция с системой мониторинга
   - Алерты при сбоях парсинга
   - Уведомления о новых отзывах

2. **Безопасность**
   - Добавить аутентификацию для API
   - Rate limiting на уровне приложения

3. **Оптимизация**
   - Кэширование часто запрашиваемых данных
   - Оптимизация запросов к БД

4. **Функциональность**
   - Экспорт данных в различные форматы
   - Анализ настроений в отзывах
   - Фильтрация отзывов с фотографиями

## 🔐 Безопасность

- PostgreSQL пароль хранится в environment variables
- SSL/TLS шифрование через Let's Encrypt
- CORS настроен для всех доменов (рекомендуется ограничить)
- Rate limiting через nginx
- Firewall правила для Docker сети

## 📝 Файловая структура

```
/root/projects/reviews-parser/
├── api_v2.py                    # FastAPI приложение с поддержкой фотографий
├── database.py                  # SQLAlchemy модели (с полями для фото)
├── parser.py                    # Парсер 2GIS (с извлечением фотографий)
├── daily_parse.py               # Инкрементальный парсинг (новый)
├── setup_cron.sh                # Настройка автоматического парсинга
├── run_daily_parse.sh           # Wrapper для cron (создается автоматически)
├── migrate_to_db.py             # Миграция данных
├── parse_sandyq_tary.py         # Парсинг всех филиалов
├── analyze_reviews.py           # Анализ отзывов
├── requirements.txt             # Python зависимости
├── .env                         # Конфигурация
├── docker-compose.yml           # Docker конфигурация
├── Dockerfile                   # Docker образ
├── reviews-api.service          # Systemd сервис
├── setup_deployment.sh          # Скрипт установки
├── nginx-reviews.conf           # Конфигурация nginx
├── CLAUDE.md                    # Документация проекта
├── data/                        # Исходные данные
│   └── sandyq_tary_branches.csv # Список филиалов
├── logs/                        # Логи системы
│   ├── cron.log                 # Логи cron заданий
│   └── daily_parse_*.log        # Логи парсинга
└── output/                      # Результаты парсинга
    ├── reviews_*.csv
    └── reviews_*.json
```

## 🆘 Поддержка

При возникновении проблем:
1. Проверить логи: `journalctl -u reviews-api.service -n 100`
2. Проверить статус БД: `docker ps | grep reviews-db`
3. Проверить nginx: `docker logs hr-nginx --tail 50`
4. Проверить автоматический парсинг: `tail -f logs/cron.log`
5. Проверить этот документ для решения типичных проблем

## 🔗 Примеры API запросов

### Получение отзывов с фотографиями:
```bash
curl "https://reviews.aqniet.site/api/v1/reviews?branch_id=70000001067929337&limit=10" | jq '.[] | select(.photos_count > 0)'
```

### Статистика по филиалу:
```bash
curl "https://reviews.aqniet.site/api/v1/branches/70000001067929337/stats" | jq .
```

### Общая статистика системы:
```bash
curl "https://reviews.aqniet.site/api/v1/stats" | jq .
```

---
Последнее обновление: 2025-07-09 19:53  
Версия: 2.1.0 (с поддержкой фотографий и автоматическим парсингом)