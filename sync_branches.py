#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для синхронизации филиалов из Google Sheets в базу данных.
Автоматически добавляет новые филиалы и обновляет существующие.
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from database import Branch, Review
from branches_loader import load_branches_from_csv
from cache_manager import get_cache_manager
import requests

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Подключение к базе данных
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL не задан в переменных окружения")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def parse_new_branch_immediately(branch_id: str, branch_name: str, session):
    """Немедленный парсинг отзывов для нового филиала"""
    try:
        from parser import TwoGISReviewsParser
        
        logger.info(f"🚀 Запуск немедленного парсинга для нового филиала: {branch_name} (ID: {branch_id})")
        
        parser = TwoGISReviewsParser()
        reviews = parser.parse_all_reviews(branch_id, branch_name)
        
        if not reviews:
            logger.warning(f"⚠️ Отзывы не найдены для нового филиала {branch_name}")
            return 0
        
        logger.info(f"📥 Получено {len(reviews)} отзывов для нового филиала")
        
        # Добавляем отзывы в базу данных
        new_count = 0
        for review_data in reviews:
            review_id = review_data.get('id') or review_data.get('review_id')
            
            if not review_id:
                continue
                
            # Преобразование даты
            date_str = review_data.get('date_created', '')
            date_created = None
            if date_str:
                try:
                    date_created = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    try:
                        date_created = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        pass
            
            review = Review(
                review_id=review_id,
                branch_id=branch_id,
                branch_name=branch_name,
                user_name=review_data.get('user', {}).get('name', 'Аноним'),
                rating=int(review_data.get('rating', 0)),
                text=review_data.get('text', ''),
                date_created=date_created,
                is_verified=review_data.get('verified', False),
                likes_count=review_data.get('likes_count', 0),
                comments_count=review_data.get('comments_count', 0),
                photos_count=review_data.get('photos_count', 0),
                photos_urls=review_data.get('photos_urls', [])
            )
            
            session.add(review)
            new_count += 1
        
        session.commit()
        logger.info(f"✅ Добавлено {new_count} отзывов для нового филиала {branch_name}")
        return new_count
        
    except Exception as e:
        logger.error(f"❌ Ошибка при парсинге нового филиала {branch_name}: {e}")
        session.rollback()
        return 0


def sync_branches_to_db():
    """Синхронизация филиалов из Google Sheets в базу данных"""
    session = SessionLocal()
    try:
        # Загрузка филиалов из Google Sheets
        logger.info("Загрузка филиалов из Google Sheets...")
        branches_data = load_branches_from_csv()
        
        if not branches_data:
            logger.error("Не удалось загрузить данные филиалов")
            return False
            
        logger.info(f"Загружено {len(branches_data)} филиалов из Google Sheets")
        
        # Получаем все существующие филиалы из БД
        existing_branches = {b.branch_id: b for b in session.query(Branch).all()}
        logger.info(f"В базе данных найдено {len(existing_branches)} филиалов")
        
        added_count = 0
        updated_count = 0
        new_branches = []  # Список новых филиалов для немедленного парсинга
        
        # Синхронизация каждого филиала
        for branch_data in branches_data:
            branch_id = branch_data.get('id_2gis')
            branch_name = branch_data.get('name')
            city = branch_data.get('city', '')
            address = branch_data.get('address', '')
            
            if not branch_id or not branch_name:
                logger.warning(f"Пропущен филиал без ID или названия: {branch_data}")
                continue
                
            if branch_id in existing_branches:
                # Обновление существующего филиала
                branch = existing_branches[branch_id]
                if (branch.branch_name != branch_name or 
                    branch.city != city or 
                    branch.address != address):
                    branch.branch_name = branch_name
                    branch.city = city
                    branch.address = address
                    branch.updated_at = datetime.utcnow()
                    updated_count += 1
                    logger.info(f"Обновлен филиал: {branch_name} (ID: {branch_id})")
            else:
                # Добавление нового филиала
                new_branch = Branch(
                    branch_id=branch_id,
                    branch_name=branch_name,
                    city=city,
                    address=address
                )
                session.add(new_branch)
                added_count += 1
                new_branches.append((branch_id, branch_name))
                logger.info(f"Добавлен новый филиал: {branch_name} (ID: {branch_id})")
        
        # Сохранение изменений
        session.commit()
        
        logger.info(f"\n✅ Синхронизация завершена:")
        logger.info(f"  - Добавлено новых филиалов: {added_count}")
        logger.info(f"  - Обновлено филиалов: {updated_count}")
        logger.info(f"  - Всего филиалов в БД: {len(existing_branches) + added_count}")
        
        # Немедленный парсинг новых филиалов
        total_new_reviews = 0
        if new_branches:
            logger.info(f"\n🚀 Запуск немедленного парсинга для {len(new_branches)} новых филиалов...")
            for branch_id, branch_name in new_branches:
                new_reviews_count = parse_new_branch_immediately(branch_id, branch_name, session)
                total_new_reviews += new_reviews_count
        
        # Очистка кэша если были изменения или новые отзывы
        if added_count > 0 or updated_count > 0 or total_new_reviews > 0:
            logger.info("🔄 Очистка кэша API...")
            try:
                # Очистка Redis кэша
                cache = get_cache_manager()
                if cache.is_available():
                    cache.invalidate_all_cache()
                    logger.info("✅ Redis кэш очищен")
                
                # Очистка API кэша через HTTP запрос
                try:
                    response = requests.post("http://127.0.0.1:8004/api/v1/cache/clear", timeout=5)
                    if response.status_code == 200:
                        logger.info("✅ API кэш очищен")
                    else:
                        logger.warning(f"⚠️ Не удалось очистить API кэш: {response.status_code}")
                except requests.RequestException as e:
                    logger.warning(f"⚠️ Не удалось подключиться к API для очистки кэша: {e}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при очистке кэша: {e}")
        
        # Отправка уведомлений если добавлены отзывы для новых филиалов
        if total_new_reviews > 0:
            logger.info(f"📱 Добавление уведомлений в очередь для {total_new_reviews} новых отзывов...")
            try:
                from telegram_notifications_queue import send_notifications_for_new_reviews
                send_notifications_for_new_reviews()
                logger.info("✅ Telegram уведомления добавлены в очередь")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при добавлении уведомлений в очередь: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {e}")
        session.rollback()
        return False
    finally:
        session.close()


if __name__ == "__main__":
    success = sync_branches_to_db()
    sys.exit(0 if success else 1)