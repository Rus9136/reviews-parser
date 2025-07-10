#!/usr/bin/env python3
"""
Модуль для отправки Telegram уведомлений через очередь
"""
import logging
import os
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import SessionLocal, TelegramSubscription, Review
from telegram_queue import queue_notification, get_queue_status

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

def get_db():
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass

def format_review_message(review: Review, show_branch: bool = True) -> str:
    """Форматирование сообщения с отзывом"""
    rating_stars = "⭐" * int(review.rating) if review.rating else "⭐"
    
    message_text = ""
    if show_branch:
        message_text += f"📢 Новый отзыв для филиала {review.branch_name}:\n"
    
    message_text += f"👤 Автор: {review.user_name or 'Аноним'}\n"
    message_text += f"⭐ Рейтинг: {rating_stars} ({review.rating}/5)\n"
    message_text += f"📝 Текст: {review.text or 'Без текста'}\n"
    message_text += f"📅 Дата: {review.date_created.strftime('%d.%m.%Y %H:%M') if review.date_created else 'Неизвестно'}\n"
    
    if review.is_verified:
        message_text += "✅ Подтвержденный отзыв\n"
    
    return message_text

def send_review_notification(review: Review, high_priority: bool = False):
    """
    Отправить уведомление о новом отзыве через очередь
    
    Args:
        review: Объект отзыва
        high_priority: Высокий приоритет отправки
    """
    db = get_db()
    try:
        # Получаем подписчиков на данный филиал
        subscriptions = db.query(TelegramSubscription).filter(
            TelegramSubscription.branch_id == review.branch_id
        ).all()
        
        if not subscriptions:
            logger.info(f"Нет подписчиков на филиал {review.branch_name}")
            return
        
        # Форматируем сообщение
        message = format_review_message(review, show_branch=True)
        
        # Получаем фотографии если есть
        photos = []
        if review.photos_urls:
            photos = review.photos_urls[:10]  # Максимум 10 фото
        
        # Отправляем уведомления всем подписчикам
        sent_count = 0
        for subscription in subscriptions:
            try:
                task_id = queue_notification(
                    chat_id=subscription.chat_id,
                    message=message,
                    photos=photos,
                    high_priority=high_priority
                )
                sent_count += 1
                logger.info(f"Уведомление добавлено в очередь для {subscription.chat_id}, task: {task_id}")
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении уведомления в очередь для {subscription.chat_id}: {str(e)}")
        
        logger.info(f"Добавлено {sent_count} уведомлений в очередь для отзыва {review.review_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений: {str(e)}")
    finally:
        db.close()

def send_bulk_notifications(reviews: List[Review], high_priority: bool = False):
    """
    Массовая отправка уведомлений через очередь
    
    Args:
        reviews: Список отзывов
        high_priority: Высокий приоритет отправки
    """
    total_sent = 0
    for review in reviews:
        try:
            send_review_notification(review, high_priority)
            total_sent += 1
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления для отзыва {review.review_id}: {str(e)}")
    
    logger.info(f"Массовая отправка завершена: {total_sent}/{len(reviews)} уведомлений добавлено в очередь")

def get_notifications_queue_status():
    """
    Получить статус очереди уведомлений
    """
    try:
        return get_queue_status()
    except Exception as e:
        logger.error(f"Ошибка при получении статуса очереди: {str(e)}")
        return {"error": str(e)}

def send_system_notification(message: str, high_priority: bool = True):
    """
    Отправить системное уведомление всем пользователям
    
    Args:
        message: Текст системного сообщения
        high_priority: Высокий приоритет отправки
    """
    db = get_db()
    try:
        # Получаем всех пользователей
        subscriptions = db.query(TelegramSubscription).distinct(TelegramSubscription.chat_id).all()
        
        if not subscriptions:
            logger.info("Нет пользователей для отправки системного уведомления")
            return
        
        # Отправляем уведомления
        sent_count = 0
        chat_ids = set()
        
        for subscription in subscriptions:
            if subscription.chat_id not in chat_ids:
                chat_ids.add(subscription.chat_id)
                try:
                    task_id = queue_notification(
                        chat_id=subscription.chat_id,
                        message=f"🔔 Системное уведомление:\n{message}",
                        photos=None,
                        high_priority=high_priority
                    )
                    sent_count += 1
                    logger.info(f"Системное уведомление добавлено в очередь для {subscription.chat_id}, task: {task_id}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при добавлении системного уведомления в очередь для {subscription.chat_id}: {str(e)}")
        
        logger.info(f"Добавлено {sent_count} системных уведомлений в очередь")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке системных уведомлений: {str(e)}")
    finally:
        db.close()

def send_notifications_for_new_reviews():
    """
    Отправить уведомления для новых отзывов (не отправленных в Telegram)
    """
    db = get_db()
    try:
        # Получаем новые отзывы, которые еще не были отправлены
        new_reviews = db.query(Review).filter(
            Review.sent_to_telegram == False
        ).all()
        
        if not new_reviews:
            logger.info("Нет новых отзывов для отправки уведомлений")
            return
        
        logger.info(f"Найдено {len(new_reviews)} новых отзывов для отправки уведомлений")
        
        # Отправляем уведомления для каждого отзыва
        for review in new_reviews:
            try:
                send_review_notification(review, high_priority=False)
                
                # Помечаем отзыв как отправленный
                review.sent_to_telegram = True
                db.commit()
                
                # Инвалидируем кэш для филиала
                from cache_manager import get_cache_manager
                cache = get_cache_manager()
                cache.invalidate_branch_cache(review.branch_id)
                
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления для отзыва {review.review_id}: {str(e)}")
                db.rollback()
        
        logger.info(f"Завершена отправка уведомлений для {len(new_reviews)} отзывов")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений для новых отзывов: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    # Тестирование системы уведомлений
    logger.info("Тестирование системы уведомлений через очередь")
    
    # Проверяем статус очереди
    status = get_notifications_queue_status()
    logger.info(f"Статус очереди: {status}")
    
    # Отправляем тестовое системное уведомление
    send_system_notification("Тестовое уведомление системы очередей", high_priority=True)