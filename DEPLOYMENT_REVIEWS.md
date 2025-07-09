# 🚀 Reviews Parser API - Deployment Guide

## 📋 Обзор

**Домен**: https://reviews.aqniet.site/  
**Назначение**: API для доступа к отзывам из 2GIS  
**База данных**: PostgreSQL на порту 5436  
**API порт**: 8004  

## 🏗️ Архитектура

```
NGINX (hr-nginx контейнер)
└── reviews.aqniet.site → 127.0.0.1:8004 (Reviews API)
    ├── / → Информация об API
    ├── /health → Health check
    ├── /docs → Swagger UI документация
    ├── /api/v1/branches → Список филиалов
    ├── /api/v1/reviews → Отзывы с фильтрацией
    └── /api/v1/stats → Статистика
```

## 📦 Компоненты

1. **PostgreSQL база данных**
   - Контейнер: reviews-db
   - Порт: 5436
   - База: reviews_db
   - Пользователь: reviews_user

2. **FastAPI приложение**
   - Порт: 8004
   - Systemd сервис: reviews-api.service
   - Python 3.11 + venv

3. **Nginx reverse proxy**
   - SSL сертификат Let's Encrypt
   - Поддомен: reviews.aqniet.site

## 🚀 Установка

### 1. Запуск скрипта установки

```bash
cd /root/projects/reviews-parser
./setup_deployment.sh
```

### 2. Добавление конфигурации nginx

Добавьте содержимое файла `nginx-reviews.conf` в основной файл конфигурации nginx `/root/projects/hr-miniapp/nginx.conf` в секцию `http`.

### 3. Перезагрузка nginx

```bash
docker exec hr-nginx nginx -s reload
```

## 🔧 Управление

### Проверка статуса
```bash
systemctl status reviews-api.service
```

### Перезапуск API
```bash
systemctl restart reviews-api.service
```

### Просмотр логов
```bash
journalctl -u reviews-api.service -f
```

### Проверка базы данных
```bash
docker exec -it reviews-db psql -U reviews_user -d reviews_db
```

## 📊 API Endpoints

### Основные эндпоинты

- `GET /` - Информация об API
- `GET /health` - Проверка состояния
- `GET /docs` - Swagger документация
- `GET /api/v1/branches` - Список филиалов
- `GET /api/v1/branches/{branch_id}/stats` - Статистика филиала
- `GET /api/v1/reviews` - Отзывы с фильтрацией
- `GET /api/v1/reviews/{review_id}` - Конкретный отзыв
- `GET /api/v1/stats` - Общая статистика
- `GET /api/v1/stats/recent` - Недавняя активность

### Параметры фильтрации отзывов

- `branch_id` - ID филиала
- `rating` - Рейтинг (1-5)
- `verified_only` - Только подтвержденные
- `date_from` - Дата от
- `date_to` - Дата до
- `search` - Поиск по тексту
- `sort_by` - Сортировка (date_created, rating, likes_count)
- `order` - Порядок (asc, desc)
- `skip` - Пропустить записей
- `limit` - Лимит записей (max 1000)

## 🧪 Тестирование

```bash
# Health check
curl https://reviews.aqniet.site/health

# Список филиалов
curl https://reviews.aqniet.site/api/v1/branches

# Отзывы по филиалу
curl "https://reviews.aqniet.site/api/v1/reviews?branch_id=70000001057699052"

# Статистика
curl https://reviews.aqniet.site/api/v1/stats
```

## 🔄 Обновление данных

### Парсинг новых отзывов
```bash
cd /root/projects/reviews-parser
source venv/bin/activate
python parse_sandyq_tary.py
```

### Миграция в базу данных
```bash
python migrate_to_db.py
```

## 🚨 Troubleshooting

### Проблема: 502 Bad Gateway
```bash
# Проверить статус сервиса
systemctl status reviews-api.service

# Проверить порт
netstat -tlnp | grep 8004

# Перезапустить сервис
systemctl restart reviews-api.service
```

### Проблема: База данных недоступна
```bash
# Проверить контейнер
docker ps | grep reviews-db

# Перезапустить контейнер
docker restart reviews-db
```

### Проблема: SSL сертификат
```bash
# Обновить сертификат
docker run --rm -v "/root/projects/infra/infra/certbot/conf:/etc/letsencrypt" -v "/root/projects/infra/infra/certbot/www:/var/www/certbot" certbot/certbot renew -d reviews.aqniet.site

# Перезагрузить nginx
docker exec hr-nginx nginx -s reload
```

## 📝 Конфигурация

### Environment переменные (.env)
```env
DATABASE_URL=postgresql://reviews_user:reviews_password@localhost:5436/reviews_db
API_HOST=0.0.0.0
API_PORT=8004
```

### Systemd сервис
Файл: `/etc/systemd/system/reviews-api.service`

## 🔐 Безопасность

- SSL/TLS шифрование через Let's Encrypt
- CORS настроен для всех доменов
- Rate limiting в nginx
- Prepared statements в SQLAlchemy

## 📊 Мониторинг

- Health endpoint: `/health`
- Метрики в базе: таблица `parse_reports`
- Логи: `journalctl -u reviews-api.service`