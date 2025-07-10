#!/usr/bin/env python3
"""
Тест для проверки корректности callback_data кнопок
"""
import os
import sys
sys.path.append('.')

from telegram_bot import load_branches_from_csv

def test_callback_data():
    """Тест callback_data для кнопок"""
    print("🔍 Тестирование callback_data кнопок")
    
    # Загрузить филиалы
    branches = load_branches_from_csv()
    
    if not branches:
        print("❌ Не удалось загрузить филиалы")
        return False
    
    print(f"✅ Загружено {len(branches)} филиалов")
    
    # Проверить callback_data для каждого филиала
    for i, branch in enumerate(branches[:5]):  # Первые 5 филиалов
        branch_id = branch['id']
        branch_name = branch['name']
        
        # Тест toggle_branch callback_data
        toggle_callback = f"toggle_branch_{branch_id}|{branch_name}"
        print(f"{i+1}. {branch_name}")
        print(f"   ID: {branch_id}")
        print(f"   Toggle callback: {toggle_callback}")
        
        # Проверить парсинг
        if toggle_callback.startswith("toggle_branch_"):
            parts = toggle_callback.split("_", 2)
            if len(parts) >= 3:
                branch_part = parts[2]
                if '|' in branch_part:
                    parsed_id, parsed_name = branch_part.split('|', 1)
                    if parsed_id == branch_id and parsed_name == branch_name:
                        print(f"   ✅ Парсинг успешен: {parsed_id} | {parsed_name}")
                    else:
                        print(f"   ❌ Ошибка парсинга: {parsed_id} | {parsed_name}")
                        return False
                else:
                    print(f"   ❌ Отсутствует разделитель |")
                    return False
        
        # Тест select_branch_for_reviews callback_data
        reviews_callback = f"select_branch_for_reviews_{branch_id}|{branch_name}"
        print(f"   Reviews callback: {reviews_callback}")
        
        # Проверить парсинг
        if reviews_callback.startswith("select_branch_for_reviews_"):
            parts = reviews_callback.split("_", 4)
            if len(parts) >= 5:
                branch_part = parts[4]
                if '|' in branch_part:
                    parsed_id, parsed_name = branch_part.split('|', 1)
                    if parsed_id == branch_id and parsed_name == branch_name:
                        print(f"   ✅ Парсинг успешен: {parsed_id} | {parsed_name}")
                    else:
                        print(f"   ❌ Ошибка парсинга: {parsed_id} | {parsed_name}")
                        return False
                else:
                    print(f"   ❌ Отсутствует разделитель |")
                    return False
        
        print()
    
    print("🎉 Все тесты callback_data пройдены успешно!")
    return True

if __name__ == "__main__":
    success = test_callback_data()
    sys.exit(0 if success else 1)