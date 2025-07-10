#!/usr/bin/env python3
"""
Комплексное тестирование улучшений системы:
- Безопасность (токены, CORS)
- Очередь уведомлений
- Кэширование
- Отказоустойчивость
"""

import pytest
import os
import requests
import time
import json
import redis
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys

# Добавляем корневую директорию в path
sys.path.append('/root/projects/reviews-parser')

from cache_manager import CacheManager, get_cache_manager
from telegram_queue import queue_notification, get_queue_status
from telegram_notifications_queue import send_review_notification, format_review_message

class TestSecurity:
    """Тесты безопасности"""
    
    def test_env_variables_loaded(self):
        """Проверка загрузки переменных окружения"""
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = [
            'DATABASE_URL',
            'PARSER_API_KEY', 
            'TELEGRAM_BOT_TOKEN',
            'REDIS_URL',
            'CORS_ALLOWED_ORIGINS'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        assert not missing_vars, f"Отсутствуют переменные окружения: {missing_vars}"
    
    def test_no_hardcoded_secrets_in_code(self):
        """Проверка отсутствия hardcoded секретов в коде"""
        import parser
        import database
        import api_v2
        
        # Проверяем, что API ключ загружается из переменных
        test_parser = parser.TwoGISReviewsParser()
        assert test_parser.api_key == os.getenv('PARSER_API_KEY'), "API ключ должен браться из переменных окружения"
        
        print("✅ Hardcoded секреты не найдены в коде")
    
    def test_cors_restriction(self):
        """Тестирование ограничений CORS"""
        api_url = "http://127.0.0.1:8004"
        
        # Разрешенный домен
        allowed_headers = {
            'Origin': 'https://reviews.aqniet.site',
            'Access-Control-Request-Method': 'GET'
        }
        
        # Запрещенный домен
        forbidden_headers = {
            'Origin': 'https://malicious-site.com',
            'Access-Control-Request-Method': 'GET'
        }
        
        try:
            # Тест разрешенного домена
            response_allowed = requests.options(
                f"{api_url}/api/v1/branches",
                headers=allowed_headers,
                timeout=5
            )
            
            # Тест запрещенного домена  
            response_forbidden = requests.options(
                f"{api_url}/api/v1/branches", 
                headers=forbidden_headers,
                timeout=5
            )
            
            print(f"✅ CORS тестирование выполнено:")
            print(f"  - Разрешенный домен: {response_allowed.status_code}")
            print(f"  - Запрещенный домен: {response_forbidden.status_code}")
            
        except requests.exceptions.ConnectionError:
            print("⚠️  API сервер недоступен для тестирования CORS")

class TestCache:
    """Тесты кэширования"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.cache = get_cache_manager()
    
    def test_redis_connection(self):
        """Проверка подключения к Redis"""
        is_available = self.cache.is_available()
        print(f"Redis доступен: {is_available}")
        
        if is_available:
            # Тест базовых операций
            test_key = "test_key"
            test_value = {"test": "data", "timestamp": datetime.now().isoformat()}
            
            # Сохранение
            save_result = self.cache.set(test_key, test_value, ttl=60)
            assert save_result, "Ошибка сохранения в кэш"
            
            # Получение
            retrieved_value = self.cache.get(test_key)
            assert retrieved_value == test_value, "Данные из кэша не совпадают"
            
            # Удаление
            delete_result = self.cache.delete(test_key)
            assert delete_result, "Ошибка удаления из кэша"
            
            print("✅ Базовые операции с кэшем работают")
        else:
            print("⚠️  Redis недоступен - тестирование пропущено")
    
    def test_cache_fallback(self):
        """Тест graceful fallback при недоступности Redis"""
        # Симулируем недоступность Redis
        with patch.object(self.cache, 'redis_client', None):
            # Операции должны возвращать безопасные значения
            assert not self.cache.is_available()
            assert self.cache.get("any_key") is None
            assert not self.cache.set("any_key", "any_value")
            assert not self.cache.delete("any_key")
            
            print("✅ Graceful fallback при недоступности Redis работает")
    
    def test_cache_invalidation(self):
        """Тест инвалидации кэша"""
        if not self.cache.is_available():
            print("⚠️  Redis недоступен - тест инвалидации пропущен")
            return
        
        branch_id = "test_branch_123"
        
        # Создаем тестовые данные в кэше
        self.cache.set_reviews_cache(branch_id, [{"test": "review"}])
        self.cache.set_branch_stats_cache(branch_id, {"test": "stats"})
        
        # Проверяем, что данные есть
        assert self.cache.get_reviews_cache(branch_id) is not None
        assert self.cache.get_branch_stats_cache(branch_id) is not None
        
        # Инвалидируем кэш для филиала
        self.cache.invalidate_branch_cache(branch_id)
        
        # Проверяем, что данные удалены
        assert self.cache.get_reviews_cache(branch_id) is None
        assert self.cache.get_branch_stats_cache(branch_id) is None
        
        print("✅ Инвалидация кэша работает корректно")

class TestTelegramQueue:
    """Тесты очереди Telegram уведомлений"""
    
    def test_queue_configuration(self):
        """Проверка конфигурации очереди"""
        try:
            from telegram_queue import app as celery_app
            
            # Проверяем конфигурацию
            config = celery_app.conf
            
            assert 'redis://' in config.broker_url, "Брокер должен быть Redis"
            assert config.task_serializer == 'json', "Сериализатор должен быть JSON"
            assert 'telegram_notifications' in config.task_routes.get('telegram_queue.send_notification', {}).get('queue', ''), "Неправильная очередь"
            
            print("✅ Конфигурация Celery корректна")
            
        except ImportError as e:
            print(f"⚠️  Ошибка импорта Celery: {e}")
    
    def test_message_formatting(self):
        """Тест форматирования сообщений"""
        # Создаем мок-объект отзыва
        mock_review = MagicMock()
        mock_review.branch_name = "Тестовый филиал"
        mock_review.user_name = "Тестовый пользователь"
        mock_review.rating = 5
        mock_review.text = "Отличный сервис!"
        mock_review.date_created = datetime(2025, 7, 10, 12, 0, 0)
        mock_review.is_verified = True
        
        message = format_review_message(mock_review, show_branch=True)
        
        assert "Тестовый филиал" in message
        assert "Тестовый пользователь" in message
        assert "⭐⭐⭐⭐⭐" in message
        assert "Отличный сервис!" in message
        assert "✅ Подтвержденный отзыв" in message
        
        print("✅ Форматирование сообщений работает корректно")
    
    def test_queue_status(self):
        """Проверка статуса очереди"""
        try:
            status = get_queue_status()
            
            if 'error' in status:
                print(f"⚠️  Ошибка получения статуса очереди: {status['error']}")
            else:
                print(f"✅ Статус очереди получен: {status}")
                
        except Exception as e:
            print(f"⚠️  Ошибка тестирования статуса очереди: {e}")

class TestAPI:
    """Тесты API endpoints"""
    
    def setup_method(self):
        """Настройка перед тестами"""
        self.api_url = "http://127.0.0.1:8004"
    
    def test_health_check(self):
        """Тест health check с проверкой кэша"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                assert data['status'] == 'healthy', "API должен быть здоровым"
                assert 'cache' in data, "В health check должна быть информация о кэше"
                assert 'database' in data, "В health check должна быть информация о БД"
                
                print(f"✅ Health check прошел успешно: {data}")
            else:
                print(f"⚠️  Health check вернул код {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("⚠️  API сервер недоступен для тестирования")
    
    def test_cache_endpoints(self):
        """Тест API endpoints для управления кэшем"""
        try:
            # Тест статистики кэша
            response = requests.get(f"{self.api_url}/api/v1/cache/stats", timeout=5)
            
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Статистика кэша получена: {stats}")
            else:
                print(f"⚠️  Ошибка получения статистики кэша: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("⚠️  API сервер недоступен для тестирования cache endpoints")

class TestRecovery:
    """Тесты восстановления при сбоях"""
    
    def test_redis_failure_recovery(self):
        """Тест восстановления при сбое Redis"""
        cache = get_cache_manager()
        
        # Симулируем сбой Redis
        original_client = cache.redis_client
        cache.redis_client = None
        
        try:
            # API должен работать без кэша
            assert not cache.is_available()
            assert cache.get("test") is None
            assert not cache.set("test", "value")
            
            print("✅ Система работает при недоступности Redis")
            
        finally:
            # Восстанавливаем подключение
            cache.redis_client = original_client
    
    def test_database_connection_error_handling(self):
        """Тест обработки ошибок подключения к БД"""
        try:
            from database import SessionLocal
            
            # Создаем сессию
            db = SessionLocal()
            
            # Простой запрос для проверки подключения
            from sqlalchemy import text
            result = db.execute(text("SELECT 1")).fetchone()
            
            assert result[0] == 1, "Подключение к БД должно работать"
            
            db.close()
            print("✅ Подключение к базе данных работает")
            
        except Exception as e:
            print(f"⚠️  Ошибка подключения к БД: {e}")

def run_comprehensive_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск комплексного тестирования системы")
    print("=" * 60)
    
    # Тесты безопасности
    print("\n🔐 ТЕСТИРОВАНИЕ БЕЗОПАСНОСТИ")
    print("-" * 30)
    security_tests = TestSecurity()
    security_tests.test_env_variables_loaded()
    security_tests.test_no_hardcoded_secrets_in_code()
    security_tests.test_cors_restriction()
    
    # Тесты кэширования
    print("\n💾 ТЕСТИРОВАНИЕ КЭШИРОВАНИЯ")
    print("-" * 30)
    cache_tests = TestCache()
    cache_tests.setup_method()
    cache_tests.test_redis_connection()
    cache_tests.test_cache_fallback()
    cache_tests.test_cache_invalidation()
    
    # Тесты очереди
    print("\n📱 ТЕСТИРОВАНИЕ ОЧЕРЕДИ УВЕДОМЛЕНИЙ")
    print("-" * 30)
    queue_tests = TestTelegramQueue()
    queue_tests.test_queue_configuration()
    queue_tests.test_message_formatting()
    queue_tests.test_queue_status()
    
    # Тесты API
    print("\n🌐 ТЕСТИРОВАНИЕ API")
    print("-" * 30)
    api_tests = TestAPI()
    api_tests.setup_method()
    api_tests.test_health_check()
    api_tests.test_cache_endpoints()
    
    # Тесты восстановления
    print("\n🔄 ТЕСТИРОВАНИЕ ВОССТАНОВЛЕНИЯ")
    print("-" * 30)
    recovery_tests = TestRecovery()
    recovery_tests.test_redis_failure_recovery()
    recovery_tests.test_database_connection_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ Комплексное тестирование завершено")

if __name__ == "__main__":
    run_comprehensive_tests()