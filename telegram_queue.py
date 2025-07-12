"""
Очередь для отправки Telegram уведомлений
"""
import os
import logging
import asyncio
from typing import List, Optional
from celery import Celery
from celery.exceptions import Retry
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError, RetryAfter, TimedOut
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Celery
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
app = Celery('telegram_queue', broker=redis_url, backend=redis_url)

# Настройка Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Almaty',
    enable_utc=True,
    task_routes={
        'telegram_queue.send_notification': {'queue': 'telegram_notifications'},
        'telegram_queue.send_notification_with_retry': {'queue': 'telegram_notifications'},
    },
    task_annotations={
        'telegram_queue.send_notification': {'rate_limit': '30/s'},
        'telegram_queue.send_notification_with_retry': {'rate_limit': '30/s'},
    },
    task_default_queue='telegram_notifications',
    worker_prefetch_multiplier=1,
    task_max_retries=3,
    task_retry_delay=60,
)

# Инициализация Telegram Bot
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

bot = Bot(token=BOT_TOKEN)

async def _send_telegram_message(chat_id: int, message: str, photos: Optional[List[str]] = None):
    """
    Асинхронная отправка сообщения в Telegram
    """
    async with bot:
        if photos and len(photos) > 0:
            # Отправляем сообщение с фотографиями
            if len(photos) == 1:
                # Одна фотография
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photos[0],
                    caption=message,
                    parse_mode='HTML'
                )
            else:
                # Несколько фотографий (альбом)
                media_group = []
                for i, photo_url in enumerate(photos[:10]):  # Максимум 10 фото
                    media = InputMediaPhoto(
                        media=photo_url,
                        caption=message if i == 0 else ""  # Подпись только к первому фото
                    )
                    media_group.append(media)
                
                await bot.send_media_group(
                    chat_id=chat_id,
                    media=media_group
                )
        else:
            # Отправляем только текст
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )

@app.task(bind=True, max_retries=3)
def send_notification(self, chat_id: int, message: str, photos: Optional[List[str]] = None):
    """
    Отправка уведомления в Telegram
    
    Args:
        chat_id: ID чата для отправки
        message: Текст сообщения
        photos: Список URL фотографий (опционально)
    """
    try:
        logger.info(f"Отправка уведомления в чат {chat_id}")
        
        # Запускаем асинхронную функцию
        asyncio.run(_send_telegram_message(chat_id, message, photos))
        
        logger.info(f"Уведомление успешно отправлено в чат {chat_id}")
        return {"status": "success", "chat_id": chat_id}
        
    except RetryAfter as e:
        # Telegram просит подождать
        logger.warning(f"Rate limit для чата {chat_id}, ожидание {e.retry_after} секунд")
        raise self.retry(countdown=e.retry_after, exc=e)
        
    except TimedOut:
        # Таймаут
        logger.warning(f"Таймаут при отправке в чат {chat_id}")
        raise self.retry(countdown=30, exc=TimedOut("Timeout"))
        
    except TelegramError as e:
        # Другие ошибки Telegram
        logger.error(f"Ошибка Telegram при отправке в чат {chat_id}: {str(e)}")
        if "Forbidden" in str(e):
            # Пользователь заблокировал бота или удалил чат
            logger.error(f"Пользователь {chat_id} заблокировал бота")
            return {"status": "blocked", "chat_id": chat_id, "error": str(e)}
        else:
            # Повторяем попытку для других ошибок
            raise self.retry(countdown=60, exc=e)
            
    except Exception as e:
        # Неожиданная ошибка
        logger.error(f"Неожиданная ошибка при отправке в чат {chat_id}: {str(e)}")
        raise self.retry(countdown=60, exc=e)

@app.task(bind=True, max_retries=5)
def send_notification_with_retry(self, chat_id: int, message: str, photos: Optional[List[str]] = None):
    """
    Отправка уведомления с расширенными повторами
    
    Args:
        chat_id: ID чата для отправки
        message: Текст сообщения
        photos: Список URL фотографий (опционально)
    """
    try:
        return send_notification(chat_id, message, photos)
    except Exception as e:
        logger.error(f"Ошибка при отправке с повторами в чат {chat_id}: {str(e)}")
        # Увеличиваем задержку с каждой попыткой
        countdown = 60 * (2 ** self.request.retries)  # Exponential backoff
        raise self.retry(countdown=countdown, exc=e, max_retries=5)

def queue_notification(chat_id: int, message: str, photos: Optional[List[str]] = None, high_priority: bool = False):
    """
    Добавляет уведомление в очередь
    
    Args:
        chat_id: ID чата для отправки
        message: Текст сообщения
        photos: Список URL фотографий (опционально)
        high_priority: Высокий приоритет (отправить быстрее)
    """
    try:
        if high_priority:
            # Высокоприоритетные сообщения отправляем с повторами
            task = send_notification_with_retry.delay(chat_id, message, photos)
        else:
            # Обычные сообщения
            task = send_notification.delay(chat_id, message, photos)
        
        logger.info(f"Уведомление добавлено в очередь для чата {chat_id}, task_id: {task.id}")
        return task.id
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении уведомления в очередь: {str(e)}")
        raise

def get_queue_status():
    """
    Получение статуса очереди
    """
    try:
        inspect = app.control.inspect()
        active_tasks = inspect.active()
        reserved_tasks = inspect.reserved()
        
        return {
            "active_tasks": len(active_tasks.get('celery@hostname', [])) if active_tasks else 0,
            "reserved_tasks": len(reserved_tasks.get('celery@hostname', [])) if reserved_tasks else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статуса очереди: {str(e)}")
        return {"error": str(e)}

if __name__ == '__main__':
    # Запуск воркера
    logger.info("Запуск Celery воркера для Telegram уведомлений")
    app.worker_main(['worker', '--loglevel=info', '--queues=telegram_notifications'])