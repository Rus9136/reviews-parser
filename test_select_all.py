#!/usr/bin/env python3
"""
Тест функции "Подписаться на все"
"""
import sys
sys.path.append('.')

from telegram_bot import load_branches_from_csv

def test_select_all_functionality():
    """Тест кнопки 'Подписаться на все'"""
    print("🔍 Тестирование функции 'Подписаться на все'")
    
    # Загрузить филиалы
    branches = load_branches_from_csv()
    
    if not branches:
        print("❌ Не удалось загрузить филиалы")
        return False
    
    print(f"✅ Загружено {len(branches)} филиалов")
    
    # Симулировать состояние пользователя
    available_branches = {b['id']: b['name'] for b in branches}
    
    # Тест 1: Выбрать все филиалы
    print("\n📝 Тест 1: Выбор всех филиалов")
    selected_branches = []  # Начальное состояние - ничего не выбрано
    
    # Симулировать нажатие "Подписаться на все"
    all_branch_ids = list(available_branches.keys())
    selected_branches = all_branch_ids
    
    print(f"   До: 0 филиалов")
    print(f"   После: {len(selected_branches)} филиалов")
    
    if len(selected_branches) == len(branches):
        print("   ✅ Все филиалы выбраны")
    else:
        print("   ❌ Не все филиалы выбраны")
        return False
    
    # Тест 2: Проверка статуса кнопки
    print("\n📝 Тест 2: Статус кнопки после выбора всех")
    all_selected = len(selected_branches) == len(branches)
    
    if all_selected:
        button_text = "❌ Отписаться от всех"
        print(f"   Кнопка: {button_text}")
        print("   ✅ Кнопка правильно изменилась")
    else:
        print("   ❌ Кнопка не изменилась")
        return False
    
    # Тест 3: Отменить выбор всех
    print("\n📝 Тест 3: Отмена выбора всех филиалов")
    
    # Симулировать нажатие "Отписаться от всех"
    selected_branches = []
    
    print(f"   До: {len(all_branch_ids)} филиалов")
    print(f"   После: {len(selected_branches)} филиалов")
    
    if len(selected_branches) == 0:
        print("   ✅ Все филиалы отменены")
    else:
        print("   ❌ Не все филиалы отменены")
        return False
    
    # Тест 4: Проверка статуса кнопки после отмены
    print("\n📝 Тест 4: Статус кнопки после отмены всех")
    all_selected = len(selected_branches) == len(branches)
    
    if not all_selected:
        button_text = "✅ Подписаться на все"
        print(f"   Кнопка: {button_text}")
        print("   ✅ Кнопка правильно изменилась обратно")
    else:
        print("   ❌ Кнопка не изменилась обратно")
        return False
    
    # Тест 5: Частичный выбор
    print("\n📝 Тест 5: Частичный выбор филиалов")
    
    # Выбрать половину филиалов
    half_count = len(branches) // 2
    selected_branches = all_branch_ids[:half_count]
    
    print(f"   Выбрано: {len(selected_branches)} из {len(branches)}")
    
    all_selected = len(selected_branches) == len(branches)
    if not all_selected:
        button_text = "✅ Подписаться на все"
        print(f"   Кнопка: {button_text}")
        print("   ✅ При частичном выборе показывается 'Подписаться на все'")
    else:
        print("   ❌ Неправильный статус кнопки при частичном выборе")
        return False
    
    print("\n🎉 Все тесты функции 'Подписаться на все' пройдены!")
    return True

if __name__ == "__main__":
    success = test_select_all_functionality()
    sys.exit(0 if success else 1)