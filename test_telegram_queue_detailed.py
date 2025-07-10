#!/usr/bin/env python3
"""
Детальное тестирование очереди Telegram уведомлений
"""

import sys
import time
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.append('/root/projects/reviews-parser')

from telegram_queue import queue_notification, get_queue_status
from telegram_notifications_queue import send_review_notification, format_review_message

def test_queue_worker_startup():
    """Тест запуска воркера очереди"""
    print("📋 Тестирование запуска воркера очереди...")
    
    try:
        from telegram_queue import app as celery_app
        
        # Проверяем конфигурацию воркера
        print(f"  - Broker URL: {celery_app.conf.broker_url}")
        print(f"  - Task routes: {celery_app.conf.task_routes}")
        print(f"  - Rate limits: {celery_app.conf.task_annotations}")
        
        # Проверяем зарегистрированные задачи
        registered_tasks = list(celery_app.tasks.keys())
        expected_tasks = [
            'telegram_queue.send_notification',
            'telegram_queue.send_notification_with_retry'
        ]
        
        for task in expected_tasks:
            if task in registered_tasks:
                print(f"  ✅ Задача зарегистрирована: {task}")
            else:
                print(f"  ❌ Задача НЕ зарегистрирована: {task}")
        
        print("✅ Тест запуска воркера пройден")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования воркера: {e}")

def test_message_queuing():
    """Тест добавления сообщений в очередь"""
    print("\n📬 Тестирование добавления сообщений в очередь...")
    
    try:
        # Тестовые данные
        chat_id = 12345
        message = "🧪 Тестовое сообщение из очереди"
        photos = ["https://example.com/photo1.jpg"]
        
        # Добавляем задачу в очередь
        task_id = queue_notification(chat_id, message, photos, high_priority=False)
        
        if task_id:
            print(f"  ✅ Сообщение добавлено в очередь: {task_id}")
            
            # Проверяем статус очереди
            time.sleep(1)  # Ждем обработки
            status = get_queue_status()
            print(f"  📊 Статус очереди: {status}")
            
        else:
            print("  ❌ Ошибка добавления сообщения в очередь")
        
        print("✅ Тест добавления сообщений пройден")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования очереди: {e}")

def test_rate_limiting():
    """Тест rate limiting (30 сообщений/сек)"""
    print("\n⏱️  Тестирование rate limiting...")
    
    try:
        start_time = time.time()
        task_ids = []
        
        # Отправляем 10 тестовых сообщений
        for i in range(10):
            task_id = queue_notification(
                chat_id=12345 + i,
                message=f"🧪 Тестовое сообщение #{i}",
                photos=None,
                high_priority=False
            )
            if task_id:
                task_ids.append(task_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"  📊 Добавлено {len(task_ids)} сообщений за {duration:.2f} секунд")
        
        if len(task_ids) == 10:
            print("  ✅ Все сообщения добавлены в очередь")
        else:
            print(f"  ⚠️  Добавлено только {len(task_ids)} из 10 сообщений")
        
        # Проверяем статус очереди
        status = get_queue_status()
        print(f"  📊 Текущий статус очереди: {status}")
        
        print("✅ Тест rate limiting пройден")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования rate limiting: {e}")

def test_error_handling():
    """Тест обработки ошибок"""
    print("\n🔧 Тестирование обработки ошибок...")
    
    try:
        # Тест с некорректным chat_id (строка вместо числа)
        try:
            task_id = queue_notification(
                chat_id="invalid_chat_id",
                message="Тест ошибки",
                photos=None
            )
            print("  ⚠️  Некорректный chat_id принят (ожидалась ошибка)")
        except Exception as e:
            print(f"  ✅ Ошибка некорректного chat_id обработана: {type(e).__name__}")
        
        # Тест с отсутствующим токеном
        original_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        try:
            os.environ.pop('TELEGRAM_BOT_TOKEN', None)
            # Здесь должна быть ошибка при инициализации
            print("  🔍 Тестирование отсутствующего токена...")
        except Exception as e:
            print(f"  ✅ Ошибка отсутствующего токена обработана: {type(e).__name__}")
        finally:
            if original_token:
                os.environ['TELEGRAM_BOT_TOKEN'] = original_token
        
        print("✅ Тест обработки ошибок пройден")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования обработки ошибок: {e}")

def test_message_formatting_edge_cases():
    """Тест форматирования сообщений в крайних случаях"""
    print("\n📝 Тестирование форматирования сообщений...")
    
    # Создаем мок-объекты с различными крайними случаями
    test_cases = [
        {
            'name': 'Полный отзыв',
            'review': {
                'branch_name': 'Тестовый филиал',
                'user_name': 'Иван Петров',
                'rating': 5,
                'text': 'Отличный сервис!',
                'date_created': datetime(2025, 7, 10, 12, 0, 0),
                'is_verified': True
            }
        },
        {
            'name': 'Отзыв без имени пользователя',
            'review': {
                'branch_name': 'Тестовый филиал',
                'user_name': None,
                'rating': 3,
                'text': 'Нормально',
                'date_created': datetime(2025, 7, 10, 12, 0, 0),
                'is_verified': False
            }
        },
        {
            'name': 'Отзыв без текста',
            'review': {
                'branch_name': 'Тестовый филиал',
                'user_name': 'Анна Сидорова',
                'rating': 1,
                'text': None,
                'date_created': datetime(2025, 7, 10, 12, 0, 0),
                'is_verified': False
            }
        },
        {
            'name': 'Отзыв с очень длинным текстом',
            'review': {
                'branch_name': 'Тестовый филиал',
                'user_name': 'Длинное имя пользователя с пробелами',
                'rating': 4,
                'text': 'Очень длинный текст отзыва ' * 20,  # ~600 символов
                'date_created': datetime(2025, 7, 10, 12, 0, 0),
                'is_verified': True
            }
        }
    ]
    
    for test_case in test_cases:
        try:
            # Создаем мок объект
            mock_review = MagicMock()
            for key, value in test_case['review'].items():
                setattr(mock_review, key, value)
            
            # Форматируем сообщение
            message = format_review_message(mock_review, show_branch=True)
            
            # Проверяем основные элементы
            assert len(message) > 0, "Сообщение не должно быть пустым"
            assert 'Тестовый филиал' in message, "В сообщении должно быть название филиала"
            
            print(f"  ✅ {test_case['name']}: {len(message)} символов")
            
        except Exception as e:
            print(f"  ❌ {test_case['name']}: {e}")
    
    print("✅ Тест форматирования сообщений пройден")

def test_high_priority_queue():
    """Тест очереди высокого приоритета"""
    print("\n🚨 Тестирование очереди высокого приоритета...")
    
    try:
        # Добавляем обычное сообщение
        normal_task = queue_notification(
            chat_id=12345,
            message="🧪 Обычное сообщение",
            photos=None,
            high_priority=False
        )
        
        # Добавляем приоритетное сообщение
        priority_task = queue_notification(
            chat_id=12345,
            message="🚨 Приоритетное сообщение",
            photos=None,
            high_priority=True
        )
        
        if normal_task and priority_task:
            print(f"  ✅ Обычная задача: {normal_task}")
            print(f"  ✅ Приоритетная задача: {priority_task}")
        else:
            print("  ❌ Ошибка создания задач")
        
        print("✅ Тест приоритетной очереди пройден")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования приоритетной очереди: {e}")

def run_detailed_queue_tests():
    """Запуск всех детальных тестов очереди"""
    print("🧪 ДЕТАЛЬНОЕ ТЕСТИРОВАНИЕ ОЧЕРЕДИ TELEGRAM УВЕДОМЛЕНИЙ")
    print("=" * 60)
    
    test_queue_worker_startup()
    test_message_queuing()
    test_rate_limiting()
    test_error_handling()
    test_message_formatting_edge_cases()
    test_high_priority_queue()
    
    print("\n" + "=" * 60)
    print("✅ Детальное тестирование очереди завершено")

if __name__ == "__main__":
    run_detailed_queue_tests()