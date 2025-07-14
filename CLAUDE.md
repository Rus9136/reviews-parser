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

2. **Branches Loader** (`branches_loader.py`) 🆕
   - Универсальный модуль для загрузки данных филиалов из Google Sheets
   - Кэширование данных (TTL 5 минут) для оптимизации производительности
   - Graceful fallback на CSV файл при недоступности Google Sheets
   - Интеграция с Google Sheets API через сервисный аккаунт
   - Дополнительные утилиты: поиск по ID, по названию, по iiko ID, счетчик филиалов
   - Поддержка маппинга iiko ID → branch_id для интеграции с внешними системами

2а. **Branches Sync** (`sync_branches.py`) 🆕
   - Синхронизация филиалов из Google Sheets в PostgreSQL базу данных
   - Автоматическое добавление новых филиалов и обновление существующих
   - **Немедленный парсинг** новых филиалов при их добавлении
   - Автоматическая очистка всех типов кэша при изменениях
   - Отправка Telegram уведомлений для отзывов новых филиалов
   - Детальное логирование процесса синхронизации

3. **Database** (`database.py`)
   - PostgreSQL база данных на порту 5436
   - SQLAlchemy ORM модели
   - Три таблицы: branches, reviews, parse_reports
   - Поддержка JSON для хранения фотографий
   - Индексы для оптимизации запросов

4. **API** (`api_v2.py`)
   - FastAPI приложение на порту 8004
   - RESTful endpoints для доступа к данным
   - Поддержка фотографий в API ответах
   - Swagger документация
   - CORS поддержка

5. **Migration** (`migrate_to_db.py`)
   - Скрипт для миграции данных из CSV/JSON в PostgreSQL
   - Обработка различных форматов дат
   - Создание отчетов о миграции

6. **Автоматический парсинг** (`daily_parse.py`)
   - Инкрементальный парсинг новых отзывов
   - Автоматический запуск через cron (каждые 5 минут)
   - **Интеграция с sync_branches** для синхронизации филиалов
   - Автоматическая очистка кэша при добавлении новых отзывов
   - Детальное логирование процесса
   - Создание отчетов в БД
   - Интеграция с Telegram уведомлениями

7. **Telegram Bot** (`telegram_bot.py`, `telegram_notifications.py`, `telegram_calendar.py`)
   - Уведомления о новых отзывах в реальном времени
   - Интуитивное главное меню с inline-кнопками
   - Подписка на филиалы с функцией "Подписаться на все"
   - Просмотр отзывов за период с выбором дат через календарь
   - Интерактивный календарь на русском языке
   - Управление подписками (добавление/удаление)
   - Отправка фотографий из отзывов (одиночные и альбомы)
   - Персистентные состояния пользователей в БД
   - Улучшенная обработка ошибок и восстановление сессий
   - Улучшенная навигация с кнопками возврата

7а. **Модуль аналитики** (`telegram_analytics.py`) 🆕
   - Генерация визуальных графиков для руководителей филиалов
   - График динамики среднего рейтинга по дням/неделям/месяцам
   - График количества отзывов с автоматической группировкой
   - Круговая диаграмма распределения отзывов по оценкам
   - Текстовые отчеты с автоматическими рекомендациями
   - Сравнение с предыдущими периодами
   - Интеграция с существующим календарем для выбора периода
   - Автоматическая очистка временных файлов

8. **Очередь уведомлений** (`telegram_queue.py`, `telegram_notifications_queue.py`)
   - Redis + Celery для надежной отправки уведомлений
   - Rate limiting 30 сообщений в секунду (соблюдение лимитов Telegram API)
   - Retry логика с exponential backoff при ошибках
   - Приоритетная очередь для срочных уведомлений
   - Systemd сервис для автоматического управления воркером
   - Отказоустойчивость: сообщения не теряются при сбоях

9. **Кэширование** (`cache_manager.py`)
   - Redis кэш для ускорения API запросов в 5.77 раз
   - **Трехуровневая система кэширования:**
     - branches_loader кэш (TTL 5 минут) - автоматически
     - Redis кэш - очищается при изменениях филиалов/отзывов
     - API кэш - очищается при изменениях филиалов/отзывов
   - **Автоматическая инвалидация** при добавлении новых филиалов и отзывов
   - TTL для разных типов данных (15 мин - 2 часа)
   - Graceful fallback при недоступности Redis
   - API endpoints для управления кэшем (/api/v1/cache/*)

10. **Безопасность и мониторинг**
   - Все токены в переменных окружения (.env)
   - CORS ограничен доверенными доменами
   - Комплексное тестирование (96% покрытия)
   - Детальные руководства по мониторингу и восстановлению
   - Алерты и метрики для production использования

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
- **6379** - Redis (кэш и очередь сообщений)

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
- `GET /api/v1/{branch_id}/{count}` - Последние N отзывов по ID филиала
- `GET /api/v1/by-iiko/{id_iiko}/{count}` - Последние N отзывов по iiko ID

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
TELEGRAM_BOT_TOKEN=8109477829:AAFacevlPz4uJA9EH4ezOGBw9B3Rf5kl5xA
```

### Google Sheets Integration 🆕
- **Spreadsheet ID**: `13przZzgeCQay1dhunOuMtGc-_lV6y_xGrNOtCoG3ssQ`
- **Service Account**: `sheets-editor@basic-zenith-465712-s5.iam.gserviceaccount.com`
- **Key File**: `basic-zenith-465712-s5-63bf748b2e1c.json` (в корне проекта)
- **Scopes**: `https://www.googleapis.com/auth/spreadsheets.readonly`
- **Кэширование**: 5 минут (настраивается в `branches_loader.py`)

### Nginx Configuration
⚠️ **ВАЖНО**: Nginx работает в host network mode, поэтому все upstream-ы должны использовать `127.0.0.1` вместо имен контейнеров:
```nginx
proxy_pass http://127.0.0.1:8004;  # НЕ http://reviews-api:8004
```

## 🚀 Команды управления

### Запуск/остановка сервисов
```bash
# API сервис
systemctl start reviews-api.service
systemctl stop reviews-api.service
systemctl restart reviews-api.service
systemctl status reviews-api.service

# Telegram Bot
systemctl start telegram-bot.service
systemctl stop telegram-bot.service
systemctl restart telegram-bot.service
systemctl status telegram-bot.service

# Telegram Queue (очередь уведомлений)
systemctl start telegram-queue.service
systemctl stop telegram-queue.service
systemctl restart telegram-queue.service
systemctl status telegram-queue.service
```

### Просмотр логов
```bash
# API сервис
journalctl -u reviews-api.service -f

# Telegram Bot
journalctl -u telegram-bot.service -f

# Telegram Queue
journalctl -u telegram-queue.service -f
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

### Telegram Bot
```bash
# Тестирование уведомлений
source venv/bin/activate
python telegram_notifications.py

# Запуск бота в интерактивном режиме (для тестирования)
source venv/bin/activate
python telegram_bot.py
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

- **Общее количество отзывов**: 18,861+
- **Отзывов с фотографиями**: 2,642+ (14.1%)
- **Активных филиалов**: 27 из 27 (загружаются из Google Sheets)
- **Google Sheets Integration**: ✅ Полная интеграция с кэшированием и fallback
- **Автоматический парсинг**: ✅ Настроен (каждые 5 минут) с Google Sheets
- **Немедленный парсинг**: ✅ Новые филиалы парсятся сразу при добавлении
- **Telegram Bot**: ✅ Активен с главным меню и календарем + Google Sheets
- **Функция "Подписаться на все"**: ✅ Реализована
- **Интерактивный календарь**: ✅ Интегрирован
- **Модуль аналитики**: ✅ Визуальные графики и отчеты для руководителей 🆕
- **Очередь уведомлений**: ✅ Redis + Celery (30 сообщений/сек) с отказоустойчивостью
- **Трехуровневое кэширование**: ✅ Автоматическая инвалидация при изменениях
- **Безопасность**: ✅ Токены в переменных окружения, ограниченный CORS, security заголовки
- **Отказоустойчивость**: ✅ Graceful fallback, автовосстановление, CSV fallback
- **Тестирование**: ✅ 13 тестовых файлов, комплексное покрытие аналитики 🆕
- **Мониторинг**: ✅ Детальные руководства и алерты
- **Последнее обновление**: 2025-07-14

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
├── database.py                  # SQLAlchemy модели (с полями для фото и Telegram)
├── parser.py                    # Парсер 2GIS (с извлечением фотографий)
├── branches_loader.py           # 🆕 Универсальный загрузчик филиалов из Google Sheets
├── sync_branches.py             # 🆕 Синхронизация филиалов с немедленным парсингом новых
├── daily_parse.py               # Инкрементальный парсинг (каждые 5 минут)
├── telegram_bot.py              # Telegram Bot для уведомлений
├── telegram_calendar.py         # Календарь для выбора дат
├── telegram_notifications.py    # Модуль отправки уведомлений
├── telegram_analytics.py        # 🆕 Модуль аналитики и графиков
├── setup_cron.sh                # Настройка автоматического парсинга
├── run_daily_parse.sh           # Wrapper для cron
├── migrate_to_db.py             # Миграция данных
├── migrate_to_google_sheets.py  # 🆕 Скрипт миграции CSV в Google Sheets
├── parse_sandyq_tary.py         # Парсинг всех филиалов (обновлен для Google Sheets)
├── analyze_reviews.py           # Анализ отзывов
├── requirements.txt             # Python зависимости (+ google-api-python-client, gspread)
├── .env                         # Конфигурация (+ TELEGRAM_BOT_TOKEN)
├── docker-compose.yml           # Docker конфигурация
├── Dockerfile                   # Docker образ
├── basic-zenith-465712-s5-63bf748b2e1c.json # 🆕 Ключ сервисного аккаунта Google
├── reviews-api.service          # Systemd сервис для API
├── telegram-bot.service         # Systemd сервис для Telegram Bot
├── setup_deployment.sh          # Скрипт установки
├── nginx-reviews.conf           # Конфигурация nginx
├── CLAUDE.md                    # Документация проекта (обновлена)
├── TESTING_REPORT.md            # Отчет о комплексном тестировании
├── MONITORING_GUIDE.md          # Руководство по мониторингу
├── setup_security_and_queue.md # Инструкции по настройке безопасности и очереди
├── telegram_queue.py            # Модуль очереди Celery для уведомлений
├── telegram_notifications_queue.py  # Уведомления через очередь
├── cache_manager.py             # Менеджер кэширования Redis
├── telegram-queue.service       # Systemd сервис для воркера очереди
├── .env.example                 # Пример конфигурации
├── test_full_system.py          # Полное тестирование системы
├── test_bot.py                  # Базовые тесты бота
├── test_buttons.py              # Тестирование callback_data
├── test_subscriptions.py        # Тестирование логики подписок
├── test_select_all.py           # Тестирование функции "Подписаться на все"
├── test_error_handling.py       # Тестирование обработки ошибок
├── test_security_and_improvements.py  # Комплексное тестирование улучшений
├── test_telegram_queue_detailed.py    # Детальное тестирование очереди
├── test_failover_scenarios.py   # Тестирование отказоустойчивости
├── test_cache_performance.py    # Тестирование производительности кэша
├── test_cors_detailed.py        # Детальное тестирование CORS
├── test_analytics.py            # 🆕 Тестирование модуля аналитики
├── test_telegram_analytics.py   # 🆕 Тестирование интеграции аналитики с ботом
├── test_calendar_behavior.py    # 🆕 Тестирование нового поведения календаря
├── ANALYTICS_DOCUMENTATION.md   # 🆕 Документация по модулю аналитики
├── CALENDAR_IMPROVEMENTS.md     # 🆕 Документация улучшений календаря
├── data/                        # Исходные данные
│   └── sandyq_tary_branches.csv # Список филиалов (fallback для Google Sheets)
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

### Последние N отзывов по ID филиала:
```bash
curl "https://reviews.aqniet.site/api/v1/70000001067929337/100" | jq '.[0:3]'
```

### Последние N отзывов по iiko ID:
```bash
curl "https://reviews.aqniet.site/api/v1/by-iiko/700917ce-77e5-479a-a4a9-68c2a9e76fc2/50" | jq '.[0:3]'
```

## 📱 Telegram Bot

### Команды
- `/start` - Главное меню с навигацией
- `/unsubscribe` - Быстрый доступ к главному меню
- `/reviews` - Быстрый доступ к главному меню

### Главное меню
- **📊 Просмотр отзывов** - Выбор филиала и период просмотра
- **📈 Статистика и аналитика** - Визуальные отчеты для руководителей 🆕
- **📝 Управление подписками** - Добавление/удаление подписок
- **🔔 Подписаться на уведомления** - Для новых пользователей
- **ℹ️ Помощь** - Справочная информация

### Функции подписок
- **✅ Подписаться на все** - Выбор всех 23 филиалов одним нажатием
- **❌ Отписаться от всех** - Массовая отписка
- **Toggle-кнопки** - Индивидуальный выбор филиалов с галочками
- **Сохранение существующих** - Новые подписки добавляются к старым
- **Интеллектуальное управление** - Показ текущего статуса подписок

### Функции просмотра отзывов
- **Выбор филиала** - Из списка активных подписок
- **Диапазон дат** - Выбор через интерактивный календарь
- **Календарь на русском языке** - Удобная навигация по месяцам
- **Проверка корректности периода** - Автоматическая валидация дат
- **Пагинация** - По 5 отзывов за раз
- **Кнопка "Показать ещё"** - Для больших списков
- **Кнопка "Главное меню"** - Быстрый возврат из любого места
- **Кнопка "Выбрать другой период"** - При отсутствии отзывов

### Функции статистики и аналитики 🆕
- **Выбор филиала** - Из списка активных подписок
- **Диапазон дат** - Выбор через интерактивный календарь
- **График динамики рейтинга** - Изменение среднего рейтинга по дням
- **График количества отзывов** - Динамика поступления отзывов
- **Распределение по оценкам** - Круговая диаграмма позитивных/негативных отзывов
- **Текстовая сводка** - Детальная статистика с рекомендациями
- **Сравнение с предыдущим периодом** - Анализ изменений
- **Автоматические рекомендации** - На основе процента негативных отзывов

### Улучшения системы
- **Персистентные состояния** - Сохранение в `telegram_user_states`
- **Автоматическое восстановление** - При потере состояния сессии
- **Обработка ошибок** - Специальные сообщения для разных ошибок
- **Callback_data оптимизация** - Соблюдение лимита 64 байта
- **Отказоустойчивость** - Graceful degradation при сбоях

### База данных
- `telegram_users` - Пользователи Telegram
- `telegram_subscriptions` - Подписки на филиалы
- `telegram_user_states` - Состояния пользователей (JSON)
- `reviews.sent_to_telegram` - Флаг отправки в Telegram

### Форматы уведомлений
```
📢 Новый отзыв для филиала {branch_name}:
👤 Автор: {user_name}
⭐ Рейтинг: {rating_stars} ({rating}/5)
📝 Текст: {text}
📅 Дата: {date_created}
```

### Поддержка фотографий
- **Одиночные фото** - Отправка с caption
- **Альбомы** - До 10 фотографий в медиа-группе
- **Fallback** - Текстовое сообщение при ошибке загрузки

### Технические улучшения
- **Оптимизация callback_data** - Сокращение с 74 до 25 символов
- **Исправление Button_data_invalid** - Соблюдение лимита 64 байта
- **Восстановление состояний** - Автоматическое пересоздание при потере
- **Улучшенная обработка ошибок** - Специфичные сообщения для разных случаев
- **Персистентность данных** - Все состояния сохраняются в PostgreSQL
- **Отказоустойчивость** - Graceful degradation при сбоях
- **Интерактивный календарь** - Замена ручного ввода дат на выбор через календарь
- **Навигация по календарю** - Переключение между месяцами
- **Валидация дат** - Автоматическая проверка корректности периода

### Файлы тестирования
- `test_full_system.py` - Полное тестирование системы
- `test_bot.py` - Базовые тесты бота
- `test_buttons.py` - Тестирование callback_data
- `test_subscriptions.py` - Тестирование логики подписок
- `test_select_all.py` - Тестирование функции "Подписаться на все"
- `test_error_handling.py` - Тестирование обработки ошибок

---
Последнее обновление: 2025-07-14 16:00  
Версия: 2.9.1 (улучшено поведение календаря при генерации аналитики - мгновенная обратная связь)