#!/usr/bin/env python3
"""
Полный тест системы Reviews Parser с Telegram Bot
"""
import os
import logging
import time
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

from database import TelegramUser, TelegramSubscription, TelegramUserState, Review
from telegram_bot import load_branches_from_csv, get_user_state, save_user_state, clear_user_state
from telegram_notifications import send_notifications_sync

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

def test_branch_loading():
    """Тест загрузки филиалов"""
    print("=== Тест загрузки филиалов ===")
    branches = load_branches_from_csv()
    
    if len(branches) >= 20:
        print(f"✅ Филиалов загружено: {len(branches)}")
        print(f"   Первые 3: {[b['name'] for b in branches[:3]]}")
        return True
    else:
        print(f"❌ Недостаточно филиалов: {len(branches)}")
        return False

def test_database_tables():
    """Тест таблиц базы данных"""
    print("\n=== Тест таблиц базы данных ===")
    db = SessionLocal()
    
    try:
        # Проверить основные таблицы
        users_count = db.query(TelegramUser).count()
        subscriptions_count = db.query(TelegramSubscription).count()
        states_count = db.query(TelegramUserState).count()
        reviews_count = db.query(Review).count()
        
        print(f"✅ Пользователей: {users_count}")
        print(f"✅ Подписок: {subscriptions_count}")
        print(f"✅ Состояний: {states_count}")
        print(f"✅ Отзывов: {reviews_count}")
        
        return reviews_count > 0
        
    except Exception as e:
        print(f"❌ Ошибка при проверке таблиц: {e}")
        return False
    finally:
        db.close()

def test_user_state_persistence():
    """Тест сохранения состояний пользователей"""
    print("\n=== Тест сохранения состояний ===")
    db = SessionLocal()
    
    try:
        test_user_id = "test_user_123"
        test_state = {
            'action': 'test',
            'selected_branches': ['branch1', 'branch2'],
            'step': 'test_step'
        }
        
        # Сохранить состояние
        save_user_state(db, test_user_id, test_state)
        
        # Получить состояние
        retrieved_state = get_user_state(db, test_user_id)
        
        if retrieved_state == test_state:
            print("✅ Состояние сохранено и получено корректно")
            
            # Очистить тестовое состояние
            clear_user_state(db, test_user_id)
            
            # Проверить, что состояние удалено
            empty_state = get_user_state(db, test_user_id)
            if not empty_state:
                print("✅ Состояние успешно очищено")
                return True
            else:
                print("❌ Состояние не удалено")
                return False
        else:
            print(f"❌ Неверное состояние: {retrieved_state}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании состояний: {e}")
        return False
    finally:
        db.close()

def test_notification_system():
    """Тест системы уведомлений"""
    print("\n=== Тест системы уведомлений ===")
    
    try:
        # Запустить проверку уведомлений
        send_notifications_sync()
        print("✅ Система уведомлений работает")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в системе уведомлений: {e}")
        return False

def test_cron_jobs():
    """Тест cron заданий"""
    print("\n=== Тест cron заданий ===")
    
    try:
        import subprocess
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        
        if result.returncode == 0:
            cron_content = result.stdout
            
            # Проверить наличие необходимых заданий
            has_parsing = "run_daily_parse.sh" in cron_content
            has_cleanup = "cleanup_old_states.py" in cron_content
            
            print(f"✅ Парсинг каждые 5 минут: {'Да' if has_parsing else 'Нет'}")
            print(f"✅ Очистка состояний каждые 6 часов: {'Да' if has_cleanup else 'Нет'}")
            
            return has_parsing and has_cleanup
        else:
            print("❌ Не удалось получить cron задания")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при проверке cron: {e}")
        return False

def test_services():
    """Тест системных сервисов"""
    print("\n=== Тест системных сервисов ===")
    
    try:
        import subprocess
        
        # Проверить API сервис
        api_result = subprocess.run(['systemctl', 'is-active', 'reviews-api.service'], 
                                   capture_output=True, text=True)
        api_active = api_result.stdout.strip() == 'active'
        
        # Проверить Telegram Bot сервис
        bot_result = subprocess.run(['systemctl', 'is-active', 'telegram-bot.service'], 
                                   capture_output=True, text=True)
        bot_active = bot_result.stdout.strip() == 'active'
        
        print(f"✅ API сервис: {'Работает' if api_active else 'Не работает'}")
        print(f"✅ Telegram Bot: {'Работает' if bot_active else 'Не работает'}")
        
        return api_active and bot_active
        
    except Exception as e:
        print(f"❌ Ошибка при проверке сервисов: {e}")
        return False

def main():
    """Основная функция полного тестирования"""
    print("🔍 Полное тестирование системы Reviews Parser\n")
    
    tests = [
        ("Загрузка филиалов", test_branch_loading),
        ("Таблицы базы данных", test_database_tables),
        ("Сохранение состояний", test_user_state_persistence),
        ("Система уведомлений", test_notification_system),
        ("Cron задания", test_cron_jobs),
        ("Системные сервисы", test_services)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            time.sleep(0.5)  # Небольшая пауза между тестами
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    # Итоговые результаты
    print("\n" + "="*50)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status:<15} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система полностью готова к работе.")
    else:
        print("⚠️  Некоторые тесты не пройдены. Требуется проверка.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)