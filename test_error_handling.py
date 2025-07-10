#!/usr/bin/env python3
"""
Тест обработки ошибок при быстрых нажатиях кнопок
"""
import sys
sys.path.append('.')

from telegram_bot import get_user_state, save_user_state, clear_user_state, load_branches_from_csv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Подключение к базе данных
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_error_handling():
    """Тест обработки ошибок"""
    print("🔍 Тестирование обработки ошибок")
    
    db = SessionLocal()
    try:
        test_user_id = "test_error_user"
        
        # Очистить тестовые данные
        clear_user_state(db, test_user_id)
        
        print("✅ Тестовые данные очищены")
        
        # Тест 1: Состояние отсутствует
        print("\n📝 Тест 1: Получение отсутствующего состояния")
        user_state = get_user_state(db, test_user_id)
        
        if not user_state:
            print("   ✅ Корректно возвращается пустое состояние")
        else:
            print("   ❌ Неожиданное состояние")
            return False
        
        # Тест 2: Восстановление состояния
        print("\n📝 Тест 2: Восстановление состояния")
        branches = load_branches_from_csv()
        
        if branches:
            # Создать новое состояние как в боте
            user_state = {
                'selected_branches': [],
                'available_branches': {b['id']: b['name'] for b in branches}
            }
            save_user_state(db, test_user_id, user_state)
            
            # Проверить восстановление
            restored_state = get_user_state(db, test_user_id)
            
            if restored_state and 'available_branches' in restored_state:
                print(f"   ✅ Состояние восстановлено с {len(restored_state['available_branches'])} филиалами")
            else:
                print("   ❌ Ошибка восстановления состояния")
                return False
        else:
            print("   ❌ Не удалось загрузить филиалы")
            return False
        
        # Тест 3: Симуляция быстрых изменений
        print("\n📝 Тест 3: Симуляция быстрых изменений состояния")
        
        # Быстро изменить состояние несколько раз
        for i in range(5):
            current_state = get_user_state(db, test_user_id)
            if current_state:
                current_state['selected_branches'] = [f"branch_{i}"]
                save_user_state(db, test_user_id, current_state)
        
        final_state = get_user_state(db, test_user_id)
        if final_state and final_state.get('selected_branches') == ['branch_4']:
            print("   ✅ Быстрые изменения обработаны корректно")
        else:
            print("   ❌ Ошибка при быстрых изменениях")
            return False
        
        # Тест 4: Очистка состояния
        print("\n📝 Тест 4: Очистка состояния")
        clear_user_state(db, test_user_id)
        
        cleaned_state = get_user_state(db, test_user_id)
        if not cleaned_state:
            print("   ✅ Состояние успешно очищено")
        else:
            print("   ❌ Состояние не очищено")
            return False
        
        # Тест 5: Обработка некорректных данных
        print("\n📝 Тест 5: Обработка некорректных данных")
        
        # Сохранить некорректное состояние
        invalid_state = {
            'selected_branches': None,  # Некорректное значение
            'available_branches': {}
        }
        save_user_state(db, test_user_id, invalid_state)
        
        retrieved_state = get_user_state(db, test_user_id)
        if retrieved_state:
            # Проверить что состояние сохранилось (бот должен обработать None)
            selected = retrieved_state.get('selected_branches', [])
            if selected is None:
                print("   ✅ Некорректные данные сохранены (бот должен обработать)")
            else:
                print("   ⚠️  Данные были изменены при сохранении")
        else:
            print("   ❌ Не удалось сохранить некорректные данные")
            return False
        
        print("\n🎉 Все тесты обработки ошибок пройдены!")
        return True
        
    finally:
        # Очистить тестовые данные
        clear_user_state(db, "test_error_user")
        db.close()

if __name__ == "__main__":
    success = test_error_handling()
    sys.exit(0 if success else 1)