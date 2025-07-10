"""
Конфигурация Celery для системы очередей
"""
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Настройка Celery
app = Celery('telegram_queue')

# Конфигурация Redis
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Almaty',
    enable_utc=True,
    task_routes={
        'telegram_queue.send_notification': {'queue': 'telegram_notifications'},
        'telegram_queue.send_notification_with_retry': {'queue': 'telegram_notifications'},
    },
    # Настройки для Telegram API лимитов
    task_default_queue='telegram_notifications',
    task_default_exchange='telegram_notifications',
    task_default_routing_key='telegram_notifications',
    
    # Ограничения скорости для соблюдения лимитов Telegram API
    task_annotations={
        'telegram_queue.send_notification': {'rate_limit': '30/s'},  # 30 сообщений в секунду
        'telegram_queue.send_notification_with_retry': {'rate_limit': '30/s'},
    },
    
    # Retry настройки
    task_retry_delay=60,  # Задержка между повторами в секундах
    task_max_retries=3,   # Максимальное количество повторов
    
    # Настройки воркера
    worker_prefetch_multiplier=1,  # Обрабатывать по одной задаче за раз
    worker_max_tasks_per_child=1000,  # Перезапуск воркера после 1000 задач
)

# Автоматическое обнаружение задач
app.autodiscover_tasks(['telegram_queue'])