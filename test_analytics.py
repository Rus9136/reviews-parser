#!/usr/bin/env python3
"""
Тест модуля аналитики
"""
import os
import sys
sys.path.append('/root/projects/reviews-parser')

from datetime import datetime, timedelta
from database import SessionLocal
from telegram_analytics import TelegramAnalytics, generate_analytics_report

def test_analytics():
    """Тестирование модуля аналитики"""
    print("🧪 Тестирование модуля аналитики...")
    
    # Создание сессии БД
    db = SessionLocal()
    
    try:
        # Создание объекта аналитики
        analytics = TelegramAnalytics(db)
        
        # Тестовые данные
        branch_id = "70000001067929337"  # Один из реальных филиалов
        date_to = datetime.now()
        date_from = date_to - timedelta(days=30)  # За последние 30 дней
        
        # Получение отзывов
        print(f"📊 Получение отзывов для филиала {branch_id}...")
        reviews = analytics.get_reviews_for_period(branch_id, date_from, date_to)
        
        print(f"✅ Найдено {len(reviews)} отзывов за период {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
        
        if reviews:
            # Вычисление статистики
            print("📈 Вычисление статистики...")
            stats = analytics.calculate_statistics(reviews)
            
            print(f"📊 Статистика:")
            print(f"  • Всего отзывов: {stats['total_reviews']}")
            print(f"  • Средний рейтинг: {stats['avg_rating']}")
            print(f"  • Позитивные: {stats['positive_count']} ({stats['positive_percent']}%)")
            print(f"  • Нейтральные: {stats['neutral_count']} ({stats['neutral_percent']}%)")
            print(f"  • Негативные: {stats['negative_count']} ({stats['negative_percent']}%)")
            
            # Генерация полного отчета
            print("📊 Генерация полного отчета...")
            report = generate_analytics_report(db, branch_id, "Тестовый филиал", date_from, date_to)
            
            print("✅ Отчет сгенерирован:")
            print(f"  • Текстовая сводка: {len(report['summary_text'])} символов")
            print(f"  • График рейтинга: {report['rating_chart']}")
            print(f"  • График количества: {report['count_chart']}")
            print(f"  • Распределение: {report['distribution_chart']}")
            
            # Проверка файлов
            for file_path in report['temp_files']:
                if os.path.exists(file_path):
                    print(f"  ✅ Файл создан: {file_path}")
                else:
                    print(f"  ❌ Файл не найден: {file_path}")
            
            # Очистка временных файлов
            print("🧹 Очистка временных файлов...")
            analytics.cleanup_temp_files(report['temp_files'])
            
            print("✅ Тест успешно завершен!")
            
        else:
            print("⚠️ Нет отзывов для тестирования. Попробуйте другой филиал или период.")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    test_analytics()