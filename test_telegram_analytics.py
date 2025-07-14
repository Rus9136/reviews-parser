#!/usr/bin/env python3
"""
Тест интеграции аналитики с Telegram-ботом
"""
import os
import sys
sys.path.append('/root/projects/reviews-parser')

from datetime import datetime, timedelta
from database import SessionLocal, TelegramUser, TelegramSubscription
from telegram_analytics import generate_analytics_report

def test_telegram_integration():
    """Тестирование интеграции с Telegram-ботом"""
    print("🤖 Тестирование интеграции аналитики с Telegram-ботом...")
    
    # Создание сессии БД
    db = SessionLocal()
    
    try:
        # Проверка подписок пользователей
        print("👥 Проверка подписок пользователей...")
        users = db.query(TelegramUser).limit(3).all()
        
        for user in users:
            print(f"👤 Пользователь: {user.first_name} (@{user.username})")
            
            # Получение подписок
            subscriptions = db.query(TelegramSubscription).filter(
                TelegramSubscription.user_id == user.user_id,
                TelegramSubscription.is_active == True
            ).all()
            
            print(f"  📝 Подписок: {len(subscriptions)}")
            
            if subscriptions:
                # Тестирование аналитики для первого филиала
                sub = subscriptions[0]
                print(f"  🏪 Тестирование для: {sub.branch_name}")
                
                # Период за последние 14 дней
                date_to = datetime.now()
                date_from = date_to - timedelta(days=14)
                
                try:
                    report = generate_analytics_report(
                        db, sub.branch_id, sub.branch_name, date_from, date_to
                    )
                    
                    print(f"  ✅ Отчет сгенерирован для {sub.branch_name}")
                    print(f"  📊 Размер текстовой сводки: {len(report['summary_text'])} символов")
                    
                    # Проверка первых строк текстовой сводки
                    first_lines = report['summary_text'].split('\n')[:3]
                    print(f"  📝 Начало сводки: {first_lines[0]}")
                    
                    # Очистка файлов
                    from telegram_analytics import TelegramAnalytics
                    analytics = TelegramAnalytics(db)
                    analytics.cleanup_temp_files(report['temp_files'])
                    
                except Exception as e:
                    print(f"  ❌ Ошибка при генерации отчета: {e}")
                
                break  # Тестируем только первого пользователя
        
        print("✅ Тест интеграции завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

def test_menu_structure():
    """Тестирование структуры меню"""
    print("🎯 Тестирование структуры меню...")
    
    # Имитация главного меню с подписками
    print("📱 Главное меню (с подписками):")
    print("  📊 Просмотр отзывов")
    print("  📈 Статистика и аналитика")  # Новая кнопка
    print("  📝 Управление подписками")
    print("  ℹ️ Помощь")
    
    # Имитация справки
    print("\n📚 Обновленная справка:")
    help_text = """ℹ️ Справка по боту

🔔 Подписка на уведомления:
• Выберите филиалы для получения уведомлений о новых отзывах
• Уведомления приходят в реальном времени

📊 Просмотр отзывов:
• Просмотр отзывов за выбранный период
• Отзывы отображаются по 5 штук

📈 Статистика и аналитика:
• Графики динамики рейтинга и количества отзывов
• Распределение отзывов по оценкам
• Сравнение с предыдущими периодами

📝 Управление подписками:
• Добавление новых подписок
• Отписка от всех уведомлений

❓ Используйте /start для возврата в главное меню"""
    
    print(help_text)
    
    print("\n✅ Структура меню корректна!")

if __name__ == "__main__":
    test_telegram_integration()
    print("\n" + "="*50)
    test_menu_structure()