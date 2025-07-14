#!/usr/bin/env python3
"""
Тест главного меню бота
"""
import sys
sys.path.append('/root/projects/reviews-parser')

from telegram_bot import show_main_menu
from telegram import InlineKeyboardButton

def test_menu_buttons():
    """Тестирование кнопок главного меню"""
    print("🧪 Тестирование главного меню...")
    
    # Проверим, что кнопка аналитики есть в коде
    with open('/root/projects/reviews-parser/telegram_bot.py', 'r') as f:
        content = f.read()
        
    if 'menu_analytics' in content:
        print("✅ Кнопка 'menu_analytics' найдена в коде")
    else:
        print("❌ Кнопка 'menu_analytics' НЕ найдена в коде")
        
    if 'Статистика и аналитика' in content:
        print("✅ Текст 'Статистика и аналитика' найден в коде")
    else:
        print("❌ Текст 'Статистика и аналитика' НЕ найден в коде")
        
    if 'show_analytics_menu' in content:
        print("✅ Функция 'show_analytics_menu' найдена в коде")
    else:
        print("❌ Функция 'show_analytics_menu' НЕ найдена в коде")
        
    # Проверим импорт модуля аналитики
    try:
        from telegram_analytics import generate_analytics_report
        print("✅ Модуль telegram_analytics успешно импортирован")
    except ImportError as e:
        print(f"❌ Ошибка импорта telegram_analytics: {e}")
        
    print("\n📋 Инструкция для проверки:")
    print("1. Откройте бота в Telegram")
    print("2. Отправьте /start")
    print("3. Убедитесь, что у вас есть подписки на филиалы")
    print("4. Если подписки есть, вы должны увидеть:")
    print("   📊 Просмотр отзывов")
    print("   📈 Статистика и аналитика  ← НОВАЯ КНОПКА")
    print("   📝 Управление подписками")
    print("   ℹ️ Помощь")
    print("5. Нажмите на кнопку 'Статистика и аналитика'")
    print("6. Выберите филиал и период")
    print("7. Получите отчет с графиками")
    
    print("\n🤖 Статус бота:")
    import subprocess
    result = subprocess.run(['systemctl', 'is-active', 'telegram-bot.service'], 
                          capture_output=True, text=True)
    if result.stdout.strip() == 'active':
        print("✅ Telegram-бот запущен и работает")
    else:
        print("❌ Telegram-бот не запущен")

if __name__ == "__main__":
    test_menu_buttons()