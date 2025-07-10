#!/usr/bin/env python3
"""
Тестирование производительности кэширования
"""

import sys
import time
import requests
import json

sys.path.append('/root/projects/reviews-parser')

def test_cache_performance():
    """Тест производительности кэширования"""
    print("⚡ Тестирование производительности кэширования...")
    
    api_url = "http://127.0.0.1:8004"
    
    try:
        # 1. Очищаем кэш
        print("  🧹 Очищаем кэш...")
        requests.post(f"{api_url}/api/v1/cache/clear", timeout=5)
        
        # 2. Первый запрос (без кэша)
        print("  🔍 Первый запрос (из БД)...")
        start_time = time.time()
        response1 = requests.get(f"{api_url}/api/v1/branches", timeout=10)
        time1 = time.time() - start_time
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"    ✅ Получено {len(data1)} филиалов за {time1:.3f}с")
        
        # 3. Второй запрос (из кэша)
        print("  🚀 Второй запрос (из кэша)...")
        start_time = time.time()
        response2 = requests.get(f"{api_url}/api/v1/branches", timeout=10)
        time2 = time.time() - start_time
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"    ✅ Получено {len(data2)} филиалов за {time2:.3f}с")
        
        # 4. Сравниваем результаты
        if time1 > 0 and time2 > 0:
            speedup = time1 / time2
            print(f"  📊 Ускорение благодаря кэшу: {speedup:.2f}x")
            
            if speedup > 2:
                print("  ✅ Кэширование значительно ускоряет запросы")
            elif speedup > 1.2:
                print("  ✅ Кэширование ускоряет запросы")
            else:
                print("  ⚠️  Ускорение от кэширования незначительное")
        
        # 5. Проверяем статистику кэша
        cache_stats = requests.get(f"{api_url}/api/v1/cache/stats", timeout=5)
        if cache_stats.status_code == 200:
            stats = cache_stats.json()
            print(f"  📊 Статистика кэша:")
            print(f"    - Память: {stats.get('memory_used', 'N/A')}")
            print(f"    - Всего ключей: {stats.get('keys_total', 0)}")
            print(f"    - По типам: {stats.get('keys_by_type', {})}")
        
    except Exception as e:
        print(f"  ❌ Ошибка тестирования производительности кэша: {e}")

def test_cache_invalidation():
    """Тест инвалидации кэша"""
    print("\n🔄 Тестирование инвалидации кэша...")
    
    api_url = "http://127.0.0.1:8004"
    
    try:
        # 1. Заполняем кэш
        print("  📥 Заполняем кэш...")
        requests.get(f"{api_url}/api/v1/branches", timeout=10)
        
        # 2. Проверяем наличие данных в кэше
        cache_stats = requests.get(f"{api_url}/api/v1/cache/stats", timeout=5)
        if cache_stats.status_code == 200:
            stats = cache_stats.json()
            keys_before = stats.get('keys_total', 0)
            print(f"    📊 Ключей в кэше до очистки: {keys_before}")
        
        # 3. Очищаем кэш
        print("  🧹 Очищаем кэш...")
        clear_response = requests.post(f"{api_url}/api/v1/cache/clear", timeout=5)
        if clear_response.status_code == 200:
            print("    ✅ Кэш очищен")
        
        # 4. Проверяем очистку
        cache_stats = requests.get(f"{api_url}/api/v1/cache/stats", timeout=5)
        if cache_stats.status_code == 200:
            stats = cache_stats.json()
            keys_after = stats.get('keys_total', 0)
            print(f"    📊 Ключей в кэше после очистки: {keys_after}")
            
            if keys_after < keys_before:
                print("    ✅ Инвалидация кэша работает")
            else:
                print("    ⚠️  Кэш не был очищен полностью")
    
    except Exception as e:
        print(f"  ❌ Ошибка тестирования инвалидации кэша: {e}")

def test_cache_ttl():
    """Тест TTL кэша"""
    print("\n⏰ Тестирование TTL кэша...")
    
    try:
        from cache_manager import get_cache_manager
        
        cache = get_cache_manager()
        
        if not cache.is_available():
            print("  ⚠️  Redis недоступен - тест TTL пропущен")
            return
        
        # 1. Сохраняем данные с коротким TTL
        test_key = "test_ttl_key"
        test_value = {"test": "ttl_data", "timestamp": time.time()}
        
        print("  📥 Сохраняем данные с TTL 3 секунды...")
        cache.set(test_key, test_value, ttl=3)
        
        # 2. Сразу проверяем наличие
        data = cache.get(test_key)
        if data:
            print("    ✅ Данные сохранены и доступны")
        else:
            print("    ❌ Данные не сохранились")
            return
        
        # 3. Ждем истечения TTL
        print("  ⏳ Ждем истечения TTL (5 секунд)...")
        time.sleep(5)
        
        # 4. Проверяем отсутствие данных
        data = cache.get(test_key)
        if data is None:
            print("    ✅ Данные автоматически удалены по TTL")
        else:
            print("    ⚠️  Данные не удалились по TTL")
    
    except Exception as e:
        print(f"  ❌ Ошибка тестирования TTL: {e}")

def run_cache_performance_tests():
    """Запуск всех тестов производительности кэша"""
    print("⚡ ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ КЭШИРОВАНИЯ")
    print("=" * 60)
    
    test_cache_performance()
    test_cache_invalidation()
    test_cache_ttl()
    
    print("\n" + "=" * 60)
    print("✅ Тестирование производительности кэширования завершено")

if __name__ == "__main__":
    run_cache_performance_tests()