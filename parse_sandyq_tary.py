#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
import os
import sys
from datetime import datetime
import time
from parser import TwoGISReviewsParser

def load_branches_from_csv(csv_path):
    """Загрузка точек продаж из CSV файла"""
    branches = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as file:  # utf-8-sig для обработки BOM
            reader = csv.DictReader(file, delimiter=';')
            
            for row in reader:
                # Ищем заголовки с учетом возможных кавычек
                name_key = None
                id_key = None
                
                for key in row.keys():
                    if 'Название точки' in key:
                        name_key = key
                    elif 'ИД 2gist' in key:
                        id_key = key
                
                if not name_key or not id_key:
                    continue
                    
                name = row.get(name_key, '').strip()
                id_2gis = row.get(id_key, '').strip()
                
                # Проверяем валидность ID (исключаем пустые, "null", "NULL")
                if name and id_2gis and id_2gis.lower() not in ['', 'null']:
                    # Проверяем, что ID состоит из цифр
                    if id_2gis.isdigit():
                        branches.append({
                            'name': name,
                            'id_2gis': id_2gis
                        })
                    else:
                        print(f"⚠️  Пропущена точка '{name}' - невалидный ID: {id_2gis}")
                else:
                    if name:
                        print(f"⚠️  Пропущена точка '{name}' - отсутствует ID 2GIS")
                    
    except Exception as e:
        print(f"❌ Ошибка при чтении CSV файла: {e}")
        return []
    
    return branches

def save_summary_report(all_reviews, branches, failed_branches, timestamp):
    """Сохранение итогового отчета"""
    
    report = {
        'parse_date': timestamp,
        'total_branches': len(branches),
        'successful_branches': len(branches) - len(failed_branches),
        'failed_branches': len(failed_branches),
        'total_reviews': len(all_reviews),
        'branches_summary': [],
        'failed_branches_list': failed_branches
    }
    
    # Статистика по каждой точке
    branch_stats = {}
    for review in all_reviews:
        branch_name = review['branch_name']
        if branch_name not in branch_stats:
            branch_stats[branch_name] = {
                'count': 0,
                'ratings': [],
                'verified_count': 0
            }
        branch_stats[branch_name]['count'] += 1
        if review['rating']:
            branch_stats[branch_name]['ratings'].append(review['rating'])
        if review.get('is_verified'):
            branch_stats[branch_name]['verified_count'] += 1
    
    for branch_name, stats in branch_stats.items():
        avg_rating = sum(stats['ratings']) / len(stats['ratings']) if stats['ratings'] else 0
        report['branches_summary'].append({
            'name': branch_name,
            'reviews_count': stats['count'],
            'average_rating': round(avg_rating, 2),
            'verified_reviews': stats['verified_count']
        })
    
    # Сохраняем отчет
    report_filename = f"output/parse_report_{timestamp}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report_filename

def main():
    """Основная функция парсинга"""
    
    print("="*60)
    print("🔍 ПАРСЕР ОТЗЫВОВ 2GIS - САНДЫК ТАРЫ")
    print("="*60)
    
    # Путь к CSV файлу
    csv_path = "data/sandyq_tary_branches.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ Файл {csv_path} не найден!")
        return
    
    # Загружаем точки продаж
    branches = load_branches_from_csv(csv_path)
    
    if not branches:
        print("❌ Не удалось загрузить данные из CSV файла")
        return
    
    print(f"\n✅ Загружено {len(branches)} точек продаж")
    
    # Создаем парсер
    parser = TwoGISReviewsParser()
    
    # Переменные для сбора данных
    all_reviews = []
    failed_branches = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Создаем директорию для результатов
    os.makedirs('output', exist_ok=True)
    
    # Парсим отзывы для каждой точки
    print("\n📊 Начинаем сбор отзывов...\n")
    
    for i, branch in enumerate(branches, 1):
        print(f"[{i}/{len(branches)}] 🏪 {branch['name']}")
        print(f"    ID: {branch['id_2gis']}")
        
        try:
            reviews = parser.parse_all_reviews(branch['id_2gis'], branch['name'])
            
            if reviews:
                all_reviews.extend(reviews)
                # Статистика по точке
                ratings = [r['rating'] for r in reviews if r['rating']]
                avg_rating = sum(ratings) / len(ratings) if ratings else 0
                verified = sum(1 for r in reviews if r.get('is_verified'))
                
                print(f"    ✅ Получено отзывов: {len(reviews)}")
                print(f"    ⭐ Средний рейтинг: {avg_rating:.2f}")
                print(f"    ✔️  Подтвержденных: {verified}")
            else:
                print(f"    ⚠️  Отзывов не найдено")
                
        except Exception as e:
            print(f"    ❌ Ошибка: {str(e)}")
            failed_branches.append({
                'name': branch['name'],
                'id': branch['id_2gis'],
                'error': str(e)
            })
        
        # Прогресс бар
        progress = int((i / len(branches)) * 50)
        print(f"    [{'='*progress}{' '*(50-progress)}] {i}/{len(branches)}")
        print()
        
        # Задержка между точками
        if i < len(branches):
            time.sleep(2)
    
    # Сохраняем результаты
    if all_reviews:
        print("\n💾 Сохранение результатов...")
        
        # CSV файл
        csv_filename = f"output/reviews_sandyq_tary_{timestamp}.csv"
        fieldnames = [
            'branch_id', 'branch_name', 'review_id', 'user_name', 
            'rating', 'text', 'date_created', 'date_edited', 
            'is_verified', 'likes_count', 'comments_count'
        ]
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_reviews)
        
        # JSON файл
        json_filename = f"output/reviews_sandyq_tary_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(all_reviews, jsonfile, ensure_ascii=False, indent=2)
        
        # Сохраняем отчет
        report_filename = save_summary_report(all_reviews, branches, failed_branches, timestamp)
        
        # Итоговая статистика
        print("\n" + "="*60)
        print("📈 ИТОГОВАЯ СТАТИСТИКА")
        print("="*60)
        print(f"✅ Успешно обработано точек: {len(branches) - len(failed_branches)}/{len(branches)}")
        print(f"📝 Всего собрано отзывов: {len(all_reviews)}")
        
        if failed_branches:
            print(f"\n⚠️  Не удалось обработать {len(failed_branches)} точек:")
            for fb in failed_branches:
                print(f"   - {fb['name']} ({fb['id']}): {fb['error']}")
        
        # Общий рейтинг
        all_ratings = [r['rating'] for r in all_reviews if r['rating']]
        if all_ratings:
            overall_rating = sum(all_ratings) / len(all_ratings)
            print(f"\n⭐ Общий средний рейтинг: {overall_rating:.2f}")
        
        print(f"\n📁 Файлы сохранены:")
        print(f"   - CSV: {csv_filename}")
        print(f"   - JSON: {json_filename}")
        print(f"   - Отчет: {report_filename}")
        
    else:
        print("\n❌ Не удалось получить ни одного отзыва")
    
    print("\n✅ Парсинг завершен!")

if __name__ == "__main__":
    main()
