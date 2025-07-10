#!/usr/bin/env python3
"""
Детальное тестирование CORS
"""

import requests
import subprocess

def test_cors_detailed():
    """Детальное тестирование CORS ограничений"""
    print("🛡️  ДЕТАЛЬНОЕ ТЕСТИРОВАНИЕ CORS")
    print("=" * 50)
    
    api_url = "http://127.0.0.1:8004"
    
    # Тестовые сценарии
    test_cases = [
        {
            'name': 'Разрешенный домен (production)',
            'origin': 'https://reviews.aqniet.site',
            'expected': 'allowed'
        },
        {
            'name': 'Localhost (разработка)',
            'origin': 'http://localhost:3000',
            'expected': 'blocked'
        },
        {
            'name': 'Подозрительный домен',
            'origin': 'https://malicious-site.com',
            'expected': 'blocked'
        },
        {
            'name': 'Поддомен production',
            'origin': 'https://api.aqniet.site',
            'expected': 'blocked'
        },
        {
            'name': 'HTTP вместо HTTPS',
            'origin': 'http://reviews.aqniet.site',
            'expected': 'blocked'
        },
        {
            'name': 'Без Origin заголовка',
            'origin': None,
            'expected': 'allowed'  # Обычно разрешено для direct API calls
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Тест: {test_case['name']}")
        
        try:
            headers = {
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            if test_case['origin']:
                headers['Origin'] = test_case['origin']
            
            # CORS preflight запрос
            response = requests.options(
                f"{api_url}/api/v1/branches",
                headers=headers,
                timeout=5
            )
            
            print(f"  📊 Код ответа: {response.status_code}")
            
            # Проверяем CORS заголовки
            cors_origin = response.headers.get('Access-Control-Allow-Origin')
            cors_methods = response.headers.get('Access-Control-Allow-Methods')
            cors_headers = response.headers.get('Access-Control-Allow-Headers')
            
            print(f"  🌐 Access-Control-Allow-Origin: {cors_origin}")
            print(f"  📋 Access-Control-Allow-Methods: {cors_methods}")
            print(f"  📝 Access-Control-Allow-Headers: {cors_headers}")
            
            # Оценка результата
            if test_case['expected'] == 'allowed':
                if response.status_code == 200 and cors_origin:
                    print(f"  ✅ PASSED: Запрос разрешен как ожидалось")
                else:
                    print(f"  ❌ FAILED: Запрос должен был быть разрешен")
            else:  # blocked
                if response.status_code in [403, 400] or not cors_origin:
                    print(f"  ✅ PASSED: Запрос заблокирован как ожидалось")
                elif cors_origin == test_case['origin']:
                    print(f"  ❌ FAILED: Запрос не должен был быть разрешен")
                else:
                    print(f"  ✅ PASSED: Запрос ограничен")
                    
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    print(f"\n{'='*50}")
    print("✅ Детальное тестирование CORS завершено")

def test_security_headers():
    """Тест security заголовков"""
    print("\n🔒 ТЕСТИРОВАНИЕ SECURITY ЗАГОЛОВКОВ")
    print("=" * 50)
    
    api_url = "http://127.0.0.1:8004"
    
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        
        # Проверяем важные security заголовки
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000',
            'Content-Security-Policy': None  # Проверяем наличие
        }
        
        print("📋 Проверка security заголовков:")
        
        for header, expected in security_headers.items():
            actual = response.headers.get(header)
            
            if actual:
                if expected and actual == expected:
                    print(f"  ✅ {header}: {actual}")
                elif not expected:
                    print(f"  ✅ {header}: {actual}")
                else:
                    print(f"  ⚠️  {header}: {actual} (ожидался: {expected})")
            else:
                print(f"  ❌ {header}: отсутствует")
        
        # Проверяем отсутствие информативных заголовков
        sensitive_headers = ['Server', 'X-Powered-By', 'X-AspNet-Version']
        
        print("\n🔍 Проверка отсутствия информативных заголовков:")
        
        for header in sensitive_headers:
            if header in response.headers:
                print(f"  ⚠️  {header}: {response.headers[header]} (лучше скрыть)")
            else:
                print(f"  ✅ {header}: скрыт")
                
    except Exception as e:
        print(f"❌ Ошибка тестирования security заголовков: {e}")

if __name__ == "__main__":
    test_cors_detailed()
    test_security_headers()