#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для ежедневного инкрементального парсинга отзывов.
Добавляет в базу данных только новые отзывы.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import time
from typing import List, Dict, Set
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from parser import TwoGISReviewsParser
from database import Review, Branch, ParseReport
from parse_sandyq_tary import load_branches_from_csv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f'daily_parse_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
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


def get_existing_review_ids(session, branch_id: str) -> Set[str]:
    """Получение множества ID существующих отзывов для филиала"""
    existing_ids = session.execute(
        select(Review.review_id).where(Review.branch_id == branch_id)
    ).scalars().all()
    return set(existing_ids)


def get_latest_review_date(session, branch_id: str):
    """Получение даты последнего отзыва для филиала"""
    latest_date = session.execute(
        select(func.max(Review.date_created)).where(Review.branch_id == branch_id)
    ).scalar()
    return latest_date


def save_new_reviews_to_db(session, reviews: List[Dict], branch_id: str, branch_name: str, existing_ids: Set[str]) -> int:
    """Сохранение только новых отзывов в базу данных"""
    new_count = 0
    
    for review_data in reviews:
        review_id = review_data.get('id') or review_data.get('review_id')
        
        # Пропускаем отзывы без ID
        if not review_id:
            logger.warning(f"Пропущен отзыв без ID: {review_data.get('text', '')[:50]}...")
            continue
            
        # Пропускаем существующие отзывы
        if review_id in existing_ids:
            continue
            
        try:
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
                        logger.warning(f"Не удалось распарсить дату: {date_str}")
            
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
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении отзыва {review_id}: {e}")
            continue
    
    return new_count


def parse_branch_incrementally(parser: TwoGISReviewsParser, branch: Dict, session) -> Dict:
    """Инкрементальный парсинг отзывов для одного филиала"""
    branch_name = branch['name']
    branch_id = branch['id_2gis']
    
    logger.info(f"🔄 Начинаем парсинг филиала: {branch_name} (ID: {branch_id})")
    
    # Получаем существующие отзывы
    existing_ids = get_existing_review_ids(session, branch_id)
    latest_date = get_latest_review_date(session, branch_id)
    
    logger.info(f"  📊 В базе уже есть {len(existing_ids)} отзывов")
    if latest_date:
        logger.info(f"  📅 Последний отзыв от: {latest_date}")
    
    try:
        # Парсим все отзывы (API 2GIS не поддерживает фильтрацию по дате)
        all_reviews = parser.parse_all_reviews(branch_id, branch_name)
        
        if not all_reviews:
            logger.warning(f"  ⚠️  Не удалось получить отзывы для {branch_name}")
            return {
                'branch_name': branch_name,
                'branch_id': branch_id,
                'status': 'failed',
                'error': 'Не удалось получить отзывы',
                'total_reviews': 0,
                'new_reviews': 0
            }
        
        # Сохраняем только новые отзывы
        new_count = save_new_reviews_to_db(session, all_reviews, branch_id, branch_name, existing_ids)
        
        logger.info(f"  ✅ Добавлено новых отзывов: {new_count} из {len(all_reviews)}")
        
        return {
            'branch_name': branch_name,
            'branch_id': branch_id,
            'status': 'success',
            'total_reviews': len(all_reviews),
            'new_reviews': new_count,
            'existing_reviews': len(existing_ids)
        }
        
    except Exception as e:
        logger.error(f"  ❌ Ошибка при парсинге {branch_name}: {e}")
        return {
            'branch_name': branch_name,
            'branch_id': branch_id,
            'status': 'failed',
            'error': str(e),
            'total_reviews': 0,
            'new_reviews': 0
        }


def main():
    """Основная функция для ежедневного парсинга"""
    start_time = datetime.now()
    logger.info("🚀 Запуск ежедневного инкрементального парсинга отзывов")
    
    # Загрузка списка филиалов
    csv_path = "data/sandyq_tary_branches.csv"
    if not os.path.exists(csv_path):
        logger.error(f"❌ Файл {csv_path} не найден!")
        sys.exit(1)
    
    branches = load_branches_from_csv(csv_path)
    if not branches:
        logger.error("❌ Не удалось загрузить список филиалов")
        sys.exit(1)
    
    logger.info(f"📋 Загружено {len(branches)} филиалов для парсинга")
    
    # Инициализация парсера
    parser = TwoGISReviewsParser()
    
    # Создание сессии БД
    session = SessionLocal()
    
    try:
        # Парсинг каждого филиала
        results = []
        total_new_reviews = 0
        successful_branches = 0
        
        for i, branch in enumerate(branches, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Обработка филиала {i}/{len(branches)}")
            
            result = parse_branch_incrementally(parser, branch, session)
            results.append(result)
            
            if result['status'] == 'success':
                successful_branches += 1
                total_new_reviews += result['new_reviews']
            
            # Коммит после каждого филиала
            session.commit()
            
            # Пауза между запросами
            if i < len(branches):
                time.sleep(2)
        
        # Создание отчета о парсинге
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        report = ParseReport(
            parse_date=start_time,
            total_branches=len(branches),
            successful_branches=successful_branches,
            failed_branches=len(branches) - successful_branches,
            total_reviews=sum(r.get('total_reviews', 0) for r in results),
            new_reviews=total_new_reviews,
            duration_seconds=duration,
            errors=str([r for r in results if r['status'] == 'failed'])
        )
        
        session.add(report)
        session.commit()
        
        # Итоговая статистика
        logger.info(f"\n{'='*60}")
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА:")
        logger.info(f"  ⏱️  Время выполнения: {duration:.2f} сек")
        logger.info(f"  🏢 Обработано филиалов: {successful_branches}/{len(branches)}")
        logger.info(f"  📝 Добавлено новых отзывов: {total_new_reviews}")
        logger.info(f"  ❌ Филиалов с ошибками: {len(branches) - successful_branches}")
        
        # Вывод филиалов с новыми отзывами
        branches_with_new = [r for r in results if r.get('new_reviews', 0) > 0]
        if branches_with_new:
            logger.info("\n📌 Филиалы с новыми отзывами:")
            for r in branches_with_new:
                logger.info(f"  - {r['branch_name']}: +{r['new_reviews']} отзывов")
        
        # Отправка Telegram уведомлений если есть новые отзывы
        if total_new_reviews > 0:
            logger.info("\n📱 Добавление уведомлений в очередь...")
            try:
                from telegram_notifications_queue import send_notifications_for_new_reviews
                send_notifications_for_new_reviews()
                logger.info("✅ Telegram уведомления добавлены в очередь")
            except Exception as e:
                logger.error(f"❌ Ошибка при добавлении уведомлений в очередь: {e}")
        else:
            logger.info("\n📱 Новых отзывов нет, уведомления не требуются")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        session.rollback()
        sys.exit(1)
    finally:
        session.close()
        logger.info("\n✅ Парсинг завершен")


if __name__ == "__main__":
    main()