#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import csv
import pandas as pd
from datetime import datetime
import os
import sys

def analyze_reviews(json_file):
    """Анализ собранных отзывов"""
    
    # Загружаем данные
    with open(json_file, 'r', encoding='utf-8') as f:
        reviews = json.load(f)
    
    if not reviews:
        print("Нет данных для анализа")
        return
    
    df = pd.DataFrame(reviews)
    
    print("="*60)
    print("📊 АНАЛИЗ ОТЗЫВОВ")
    print("="*60)
    
    # Общая статистика
    print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
    print(f"Всего отзывов: {len(df)}")
    print(f"Уникальных точек: {df['branch_name'].nunique()}")
    
    # Рейтинги
    print(f"\n⭐ РЕЙТИНГИ:")
    print(f"Средний рейтинг: {df['rating'].mean():.2f}")
    print(f"Медиана: {df['rating'].median():.2f}")
    print(f"Минимальный: {df['rating'].min()}")
    print(f"Максимальный: {df['rating'].max()}")
    
    # Распределение рейтингов
    print(f"\nРаспределение оценок:")
    rating_dist = df['rating'].value_counts().sort_index()
    for rating, count in rating_dist.items():
        percentage = (count / len(df)) * 100
        stars = '⭐' * int(rating)
        print(f"{rating} {stars}: {count} ({percentage:.1f}%)")
    
    # Топ-5 лучших точек
    print(f"\n🏆 ТОП-5 ТОЧЕК ПО РЕЙТИНГУ:")
    branch_stats = df.groupby('branch_name').agg({
        'rating': ['mean', 'count'],
        'is_verified': 'sum'
    }).round(2)
    branch_stats.columns = ['avg_rating', 'review_count', 'verified_count']
    branch_stats = branch_stats.sort_values('avg_rating', ascending=False)
    
    for i, (branch, stats) in enumerate(branch_stats.head().iterrows(), 1):
        print(f"{i}. {branch}")
        print(f"   Рейтинг: {stats['avg_rating']:.2f} | Отзывов: {int(stats['review_count'])} | Подтвержденных: {int(stats['verified_count'])}")
    
    # Худшие точки
    print(f"\n📉 ТОЧКИ С НИЗКИМ РЕЙТИНГОМ (< 4.0):")
    low_rated = branch_stats[branch_stats['avg_rating'] < 4.0]
    if not low_rated.empty:
        for branch, stats in low_rated.iterrows():
            print(f"- {branch}: {stats['avg_rating']:.2f} ({int(stats['review_count'])} отзывов)")
    else:
        print("Все точки имеют рейтинг 4.0 и выше!")
    
    # Анализ по времени
    df['date_created'] = pd.to_datetime(df['date_created'])
    df['year_month'] = df['date_created'].dt.to_period('M')
    
    print(f"\n📅 ДИНАМИКА ОТЗЫВОВ:")
    recent_months = df.groupby('year_month').size().tail(6)
    for period, count in recent_months.items():
        print(f"{period}: {count} отзывов")
    
    # Анализ текстов (простой)
    print(f"\n💬 АНАЛИЗ ТЕКСТОВ:")
    df['text_length'] = df['text'].fillna('').str.len()
    print(f"Средняя длина отзыва: {df['text_length'].mean():.0f} символов")
    print(f"Отзывов без текста: {(df['text_length'] == 0).sum()}")
    
    # Верифицированные отзывы
    verified_pct = (df['is_verified'].sum() / len(df)) * 100
    print(f"\n✅ ВЕРИФИКАЦИЯ:")
    print(f"Подтвержденных отзывов: {df['is_verified'].sum()} ({verified_pct:.1f}%)")
    
    # Сохраняем детальный отчет
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"output/analysis_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        # Перенаправляем вывод в файл
        original_stdout = sys.stdout
        sys.stdout = f
        
        # Повторяем весь анализ для файла
        print("="*60)
        print("ДЕТАЛЬНЫЙ АНАЛИЗ ОТЗЫВОВ САНДЫК ТАРЫ")
        print(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Детальная статистика по каждой точке
        print("\nДЕТАЛЬНАЯ СТАТИСТИКА ПО ТОЧКАМ:")
        print("-"*60)
        
        for branch, stats in branch_stats.iterrows():
            print(f"\n{branch}")
            print(f"Средний рейтинг: {stats['avg_rating']:.2f}")
            print(f"Количество отзывов: {int(stats['review_count'])}")
            print(f"Подтвержденных: {int(stats['verified_count'])}")
            
            # Распределение оценок для точки
            branch_reviews = df[df['branch_name'] == branch]
            rating_dist = branch_reviews['rating'].value_counts().sort_index()
            print("Распределение оценок:")
            for rating, count in rating_dist.items():
                print(f"  {rating}⭐: {count}")
        
        sys.stdout = original_stdout
    
    print(f"\n📄 Детальный отчет сохранен: {report_file}")
    
    # Экспорт статистики по точкам в Excel
    excel_file = f"output/branch_statistics_{timestamp}.xlsx"
    branch_stats.to_excel(excel_file)
    print(f"📊 Статистика по точкам экспортирована: {excel_file}")

def main():
    """Главная функция"""
    
    # Ищем последний файл с отзывами
    output_dir = "output"
    json_files = [f for f in os.listdir(output_dir) if f.startswith("reviews_sandyq_tary_") and f.endswith(".json")]
    
    if not json_files:
        print("❌ Не найдено файлов с отзывами. Сначала запустите parse_sandyq_tary.py")
        return
    
    # Берем последний файл
    latest_file = sorted(json_files)[-1]
    json_path = os.path.join(output_dir, latest_file)
    
    print(f"📁 Анализируем файл: {latest_file}")
    analyze_reviews(json_path)

if __name__ == "__main__":
    main()
