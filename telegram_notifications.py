#!/usr/bin/env python3
"""
Модуль для отправки Telegram уведомлений о новых отзывах
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import List

from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import SessionLocal, TelegramSubscription, Review

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def get_db():
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass

async def send_review_message(bot: Bot, chat_id: str, review: Review, show_branch: bool = True):
    """Отправить сообщение с отзывом"""
    try:
        # Форматирование отзыва
        rating_stars = "⭐" * int(review.rating) if review.rating else "⭐"
        
        message_text = ""
        if show_branch:
            message_text += f"📢 Новый отзыв для филиала {review.branch_name}:\n"
        
        message_text += f"👤 Автор: {review.user_name or 'Аноним'}\n"
        message_text += f"⭐ Рейтинг: {rating_stars} ({review.rating}/5)\n"
        message_text += f"📝 Текст: {review.text or 'Без текста'}\n"
        message_text += f"📅 Дата: {review.date_created.strftime('%d.%m.%Y %H:%M') if review.date_created else 'Неизвестно'}\n"
        
        # Отправка фотографий если есть
        if review.photos_urls and len(review.photos_urls) > 0:
            photos = review.photos_urls[:10]  # Максимум 10 фотографий
            
            if len(photos) == 1:
                # Одна фотография
                try:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photos[0],
                        caption=message_text
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке фото: {e}")
                    # Отправить как текст если фото не получилось
                    await bot.send_message(
                        chat_id=chat_id,
                        text=message_text
                    )
            else:
                # Несколько фотографий - альбом
                try:
                    media = []
                    for i, photo_url in enumerate(photos):
                        if i == 0:
                            media.append(InputMediaPhoto(media=photo_url, caption=message_text))
                        else:
                            media.append(InputMediaPhoto(media=photo_url))
                    
                    await bot.send_media_group(
                        chat_id=chat_id,
                        media=media
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке альбома: {e}")
                    # Отправить как текст если альбом не получилось
                    await bot.send_message(
                        chat_id=chat_id,
                        text=message_text
                    )
        else:
            # Без фотографий
            await bot.send_message(
                chat_id=chat_id,
                text=message_text
            )
        
        return True
        
    except TelegramError as e:
        logger.error(f"Ошибка Telegram API при отправке сообщения пользователю {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Общая ошибка при отправке сообщения пользователю {chat_id}: {e}")
        return False

async def send_new_review_notifications():
    """Отправить уведомления о новых отзывах"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return
    
    logger.info("Проверка новых отзывов для уведомлений...")
    
    bot = Bot(token=BOT_TOKEN)
    db = get_db()
    
    try:
        # Получить неотправленные отзывы
        new_reviews = db.query(Review).filter(
            Review.sent_to_telegram == False
        ).all()
        
        if not new_reviews:
            logger.info("Новых отзывов нет")
            return
        
        logger.info(f"Найдено {len(new_reviews)} новых отзывов")
        
        # Получить все активные подписки
        subscriptions = db.query(TelegramSubscription).filter(
            TelegramSubscription.is_active == True
        ).all()
        
        if not subscriptions:
            logger.info("Нет активных подписок")
            # Все равно помечаем отзывы как отправленные
            for review in new_reviews:
                review.sent_to_telegram = True
            db.commit()
            return
        
        # Группировать подписки по филиалам
        subscriptions_by_branch = {}
        for sub in subscriptions:
            if sub.branch_id not in subscriptions_by_branch:
                subscriptions_by_branch[sub.branch_id] = []
            subscriptions_by_branch[sub.branch_id].append(sub)
        
        # Отправить уведомления
        sent_count = 0
        for review in new_reviews:
            if review.branch_id in subscriptions_by_branch:
                branch_subscriptions = subscriptions_by_branch[review.branch_id]
                
                for subscription in branch_subscriptions:
                    try:
                        success = await send_review_message(bot, subscription.user_id, review, show_branch=True)
                        if success:
                            sent_count += 1
                        
                        # Небольшая задержка для соблюдения лимитов API (не более 30 сообщений в секунду)
                        await asyncio.sleep(0.05)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления пользователю {subscription.user_id}: {e}")
            
            # Пометить отзыв как отправленный
            review.sent_to_telegram = True
        
        db.commit()
        logger.info(f"Отправлено {sent_count} уведомлений")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений: {e}")
        db.rollback()
    finally:
        db.close()

def send_notifications_sync():
    """Синхронная обертка для отправки уведомлений"""
    asyncio.run(send_new_review_notifications())

if __name__ == "__main__":
    send_notifications_sync()