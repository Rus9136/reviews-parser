#!/usr/bin/env python3
"""
Скрипт для очистки старых состояний пользователей (старше 1 часа)
"""
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

from database import TelegramUserState

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Подключение к базе данных
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def cleanup_old_states():
    """Очистить старые состояния пользователей"""
    db = SessionLocal()
    try:
        # Удалить состояния старше 1 часа
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        deleted_count = db.query(TelegramUserState).filter(
            TelegramUserState.updated_at < cutoff_time
        ).delete()
        
        db.commit()
        logger.info(f"Удалено {deleted_count} старых состояний пользователей")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке состояний: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_old_states()