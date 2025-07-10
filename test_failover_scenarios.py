#!/usr/bin/env python3
"""
Тестирование сценариев отказоустойчивости
"""

import sys
import time
import subprocess
import requests
from datetime import datetime

sys.path.append('/root/projects/reviews-parser')

def test_redis_failure_scenario():
    """Тест сценария сбоя Redis"""
    print("🔥 Тестирование сценария сбоя Redis...")
    
    api_url = "http://127.0.0.1:8004"
    
    try:
        # 1. Проверяем исходное состояние
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  📊 Исходное состояние: cache={data.get('cache', 'unknown')}")
        
        # 2. Останавливаем Redis
        print("  🛑 Останавливаем Redis...")
        subprocess.run(["docker", "stop", "reviews-redis"], 
                      capture_output=True, check=False)
        
        # Ждем, чтобы изменения вступили в силу
        time.sleep(3)
        
        # 3. Проверяем работу API без Redis
        print("  🔍 Проверяем работу API без Redis...")
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  📊 Состояние без Redis: cache={data.get('cache', 'unknown')}")
            
            # API должен работать даже без кэша
            if data['status'] == 'healthy':
                print("  ✅ API работает без Redis (graceful degradation)")
            else:
                print("  ❌ API не работает без Redis")
        
        # 4. Проверяем API endpoints без кэша
        response = requests.get(f"{api_url}/api/v1/branches", timeout=10)
        if response.status_code == 200:
            branches = response.json()
            print(f"  ✅ API branches работает без кэша: {len(branches)} филиалов")
        else:
            print(f"  ❌ API branches не работает без кэша: {response.status_code}")
        
    except Exception as e:
        print(f"  ❌ Ошибка тестирования сбоя Redis: {e}")
    
    finally:
        # 5. Восстанавливаем Redis
        print("  🔄 Восстанавливаем Redis...")
        subprocess.run(["docker", "start", "reviews-redis"], 
                      capture_output=True, check=False)
        
        # Ждем восстановления
        time.sleep(5)
        
        # Проверяем восстановление
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  📊 Состояние после восстановления: cache={data.get('cache', 'unknown')}")
                
                if data.get('cache') == 'connected':
                    print("  ✅ Redis успешно восстановлен")
                else:
                    print("  ⚠️  Redis не восстановился полностью")
        except Exception as e:
            print(f"  ⚠️  Ошибка проверки восстановления: {e}")

def test_queue_worker_failure():
    """Тест сбоя воркера очереди"""
    print("\n🔥 Тестирование сценария сбоя воркера очереди...")
    
    try:
        # 1. Останавливаем воркер очереди
        print("  🛑 Останавливаем воркер очереди...")
        result = subprocess.run(
            ["sudo", "systemctl", "stop", "telegram-queue.service"],
            capture_output=True, text=True
        )
        
        # 2. Проверяем, что сообщения все еще добавляются в очередь
        print("  🔍 Проверяем добавление сообщений без воркера...")
        
        from telegram_queue import queue_notification
        
        task_id = queue_notification(
            chat_id=12345,
            message="🧪 Тест без воркера",
            photos=None
        )
        
        if task_id:
            print(f"  ✅ Сообщения добавляются в очередь без воркера: {task_id}")
        else:
            print("  ❌ Ошибка добавления сообщений без воркера")
        
        # 3. Восстанавливаем воркер
        print("  🔄 Восстанавливаем воркер очереди...")
        result = subprocess.run(
            ["sudo", "systemctl", "start", "telegram-queue.service"],
            capture_output=True, text=True
        )
        
        time.sleep(3)
        
        # 4. Проверяем статус воркера
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", "telegram-queue.service"],
            capture_output=True, text=True
        )
        
        if result.stdout.strip() == "active":
            print("  ✅ Воркер очереди успешно восстановлен")
        else:
            print(f"  ❌ Воркер очереди не восстановился: {result.stdout.strip()}")
        
    except Exception as e:
        print(f"  ❌ Ошибка тестирования сбоя воркера: {e}")

def test_database_connection_failure():
    """Тест временного сбоя соединения с БД"""
    print("\n🔥 Тестирование сценария сбоя соединения с БД...")
    
    api_url = "http://127.0.0.1:8004"
    
    try:
        # 1. Проверяем исходное состояние
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  📊 Исходное состояние БД: {data.get('database', 'unknown')}")
        
        # 2. Останавливаем PostgreSQL
        print("  🛑 Останавливаем PostgreSQL...")
        subprocess.run(
            ["docker", "stop", "reviews-db"], 
            capture_output=True, check=False
        )
        
        time.sleep(3)
        
        # 3. Проверяем поведение API без БД
        print("  🔍 Проверяем поведение API без БД...")
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            print(f"  📊 Health check без БД: {response.status_code}")
            
            if response.status_code == 503:
                print("  ✅ API корректно возвращает 503 без БД")
            else:
                print(f"  ⚠️  Неожиданный код ответа: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("  ❌ API полностью недоступен без БД")
        except Exception as e:
            print(f"  ❌ Ошибка проверки API без БД: {e}")
        
    except Exception as e:
        print(f"  ❌ Ошибка тестирования сбоя БД: {e}")
    
    finally:
        # 4. Восстанавливаем PostgreSQL
        print("  🔄 Восстанавливаем PostgreSQL...")
        subprocess.run(
            ["docker", "start", "reviews-db"], 
            capture_output=True, check=False
        )
        
        # Ждем восстановления
        time.sleep(10)
        
        # Проверяем восстановление
        try:
            response = requests.get(f"{api_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"  📊 Состояние после восстановления БД: {data.get('database', 'unknown')}")
                
                if data.get('database') == 'connected':
                    print("  ✅ PostgreSQL успешно восстановлен")
                else:
                    print("  ⚠️  PostgreSQL не восстановился полностью")
        except Exception as e:
            print(f"  ⚠️  Ошибка проверки восстановления БД: {e}")

def test_api_restart_scenario():
    """Тест перезапуска API сервиса"""
    print("\n🔄 Тестирование перезапуска API сервиса...")
    
    api_url = "http://127.0.0.1:8004"
    
    try:
        # 1. Проверяем исходное состояние
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print("  📊 API работает до перезапуска")
        
        # 2. Перезапускаем API сервис
        print("  🔄 Перезапускаем API сервис...")
        subprocess.run(
            ["sudo", "systemctl", "restart", "reviews-api.service"],
            capture_output=True, text=True
        )
        
        # 3. Ждем запуска
        print("  ⏳ Ждем запуска API...")
        max_attempts = 30
        
        for attempt in range(max_attempts):
            try:
                time.sleep(1)
                response = requests.get(f"{api_url}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ API восстановлен за {attempt + 1} секунд")
                    print(f"  📊 Состояние: {data}")
                    break
            except:
                if attempt == max_attempts - 1:
                    print(f"  ❌ API не восстановился за {max_attempts} секунд")
        
    except Exception as e:
        print(f"  ❌ Ошибка тестирования перезапуска API: {e}")

def test_load_scenario():
    """Тест нагрузочного сценария"""
    print("\n⚡ Тестирование нагрузочного сценария...")
    
    api_url = "http://127.0.0.1:8004"
    
    try:
        start_time = time.time()
        successful_requests = 0
        failed_requests = 0
        
        # Отправляем 50 параллельных запросов
        print("  🚀 Отправляем 50 запросов к API...")
        
        import concurrent.futures
        import requests
        
        def make_request():
            try:
                response = requests.get(f"{api_url}/api/v1/branches", timeout=10)
                return response.status_code == 200
            except:
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    successful_requests += 1
                else:
                    failed_requests += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"  📊 Результаты нагрузочного теста:")
        print(f"    - Успешных запросов: {successful_requests}")
        print(f"    - Неудачных запросов: {failed_requests}")
        print(f"    - Время выполнения: {duration:.2f} секунд")
        print(f"    - RPS: {50/duration:.2f}")
        
        if successful_requests >= 45:  # 90% успешных запросов
            print("  ✅ Нагрузочный тест пройден")
        else:
            print("  ⚠️  Низкий процент успешных запросов")
        
    except Exception as e:
        print(f"  ❌ Ошибка нагрузочного тестирования: {e}")

def run_failover_tests():
    """Запуск всех тестов отказоустойчивости"""
    print("🔥 ТЕСТИРОВАНИЕ ОТКАЗОУСТОЙЧИВОСТИ СИСТЕМЫ")
    print("=" * 60)
    
    test_redis_failure_scenario()
    test_queue_worker_failure()
    test_database_connection_failure()
    test_api_restart_scenario()
    test_load_scenario()
    
    print("\n" + "=" * 60)
    print("✅ Тестирование отказоустойчивости завершено")

if __name__ == "__main__":
    run_failover_tests()