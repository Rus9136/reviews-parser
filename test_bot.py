#!/usr/bin/env python3
"""
Тестирование функций Telegram бота
"""
import asyncio
import logging
from telegram_bot import load_branches_from_csv
from telegram_notifications import send_notifications_sync

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_csv_loading():
    """Тест загрузки филиалов из CSV"""
    print("=== Тест загрузки филиалов ===")
    branches = load_branches_from_csv()
    print(f"Загружено филиалов: {len(branches)}")
    
    if branches:
        print("Первые 5 филиалов:")
        for i, branch in enumerate(branches[:5]):
            print(f"{i+1}. {branch['name']} (ID: {branch['id']})")
    else:
        print("Филиалы не загружены!")
    
    return len(branches) > 0

def test_notifications():
    """Тест отправки уведомлений"""
    print("\n=== Тест отправки уведомлений ===")
    try:
        send_notifications_sync()
        print("Тест уведомлений завершен успешно")
        return True
    except Exception as e:
        print(f"Ошибка при тестировании уведомлений: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🤖 Тестирование Telegram бота\n")
    
    # Тест загрузки филиалов
    csv_ok = test_csv_loading()
    
    # Тест уведомлений
    notifications_ok = test_notifications()
    
    # Результаты
    print(f"\n=== Результаты тестов ===")
    print(f"✅ Загрузка филиалов: {'OK' if csv_ok else 'FAIL'}")
    print(f"✅ Отправка уведомлений: {'OK' if notifications_ok else 'FAIL'}")
    
    if csv_ok and notifications_ok:
        print("🎉 Все тесты пройдены успешно!")
    else:
        print("❌ Некоторые тесты не пройдены")

if __name__ == "__main__":
    main()