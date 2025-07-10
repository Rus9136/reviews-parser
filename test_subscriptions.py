#!/usr/bin/env python3
"""
Тест логики подписок
"""
import os
import sys
sys.path.append('.')

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, and_
from dotenv import load_dotenv
from database import TelegramSubscription

# Загрузка переменных окружения
load_dotenv()

# Подключение к базе данных
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_subscription_logic():
    """Тест логики подписок"""
    print("🔍 Тестирование логики подписок")
    
    db = SessionLocal()
    try:
        # Проверить текущие подписки
        test_user_id = "test_user_123"
        
        # Очистить тестовые данные
        db.query(TelegramSubscription).filter(
            TelegramSubscription.user_id == test_user_id
        ).delete()
        db.commit()
        
        print(f"✅ Тестовые данные очищены")
        
        # Создать первоначальные подписки
        initial_branches = [
            ("70000001057699052", "Sandyq Алматы"),
            ("70000001041483077", "Sandyq Шымкент")
        ]
        
        for branch_id, branch_name in initial_branches:
            subscription = TelegramSubscription(
                user_id=test_user_id,
                branch_id=branch_id,
                branch_name=branch_name
            )
            db.add(subscription)
        
        db.commit()
        print(f"✅ Созданы первоначальные подписки: {len(initial_branches)}")
        
        # Проверить активные подписки
        active_subs = db.query(TelegramSubscription).filter(
            and_(
                TelegramSubscription.user_id == test_user_id,
                TelegramSubscription.is_active == True
            )
        ).all()
        
        print(f"✅ Активных подписок: {len(active_subs)}")
        for sub in active_subs:
            print(f"   - {sub.branch_name} ({sub.branch_id})")
        
        # Симулировать добавление новых подписок (как в реальном боте)
        # Пользователь выбирает: старые + новые
        selected_branches = [
            "70000001057699052",  # Sandyq Алматы (старая)
            "70000001041483077",  # Sandyq Шымкент (старая)
            "70000001058907834",  # Sandyq Туркестан (новая)
            "70000001065967444"   # Tary Астана (новая)
        ]
        
        print(f"\\n📝 Пользователь выбрал {len(selected_branches)} филиалов")
        
        # Логика из бота
        existing_subscriptions = db.query(TelegramSubscription).filter(
            TelegramSubscription.user_id == test_user_id
        ).all()
        
        existing_branch_ids = [sub.branch_id for sub in existing_subscriptions]
        
        # Деактивировать подписки которые сняли
        for subscription in existing_subscriptions:
            if subscription.branch_id not in selected_branches:
                subscription.is_active = False
                print(f"   ❌ Деактивирована: {subscription.branch_name}")
            elif not subscription.is_active:
                subscription.is_active = True
                print(f"   ✅ Реактивирована: {subscription.branch_name}")
        
        # Добавить новые подписки
        available_branches = {
            "70000001057699052": "Sandyq Алматы",
            "70000001041483077": "Sandyq Шымкент",
            "70000001058907834": "Sandyq Туркестан",
            "70000001065967444": "Tary Астана"
        }
        
        for branch_id in selected_branches:
            if branch_id not in existing_branch_ids:
                branch_name = available_branches.get(branch_id, 'Unknown')
                subscription = TelegramSubscription(
                    user_id=test_user_id,
                    branch_id=branch_id,
                    branch_name=branch_name
                )
                db.add(subscription)
                print(f"   ➕ Добавлена: {branch_name}")
        
        db.commit()
        
        # Проверить итоговые активные подписки
        final_active_subs = db.query(TelegramSubscription).filter(
            and_(
                TelegramSubscription.user_id == test_user_id,
                TelegramSubscription.is_active == True
            )
        ).all()
        
        print(f"\\n✅ Итоговых активных подписок: {len(final_active_subs)}")
        for sub in final_active_subs:
            print(f"   - {sub.branch_name} ({sub.branch_id})")
        
        # Проверить что получилось то что ожидалось
        expected_count = len(selected_branches)
        actual_count = len(final_active_subs)
        
        if actual_count == expected_count:
            print(f"\\n🎉 Тест пройден! Ожидалось {expected_count}, получено {actual_count}")
            return True
        else:
            print(f"\\n❌ Тест не пройден! Ожидалось {expected_count}, получено {actual_count}")
            return False
        
    finally:
        # Очистить тестовые данные
        db.query(TelegramSubscription).filter(
            TelegramSubscription.user_id == test_user_id
        ).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    success = test_subscription_logic()
    sys.exit(0 if success else 1)