import csv
import json
import os
from parser import TwoGISReviewsParser
from datetime import datetime
import time

def load_branches_from_csv(csv_path):
    """Загрузка точек продаж из CSV файла"""
    branches = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            # Читаем первую строку, чтобы понять формат
            first_line = file.readline().strip()
            file.seek(0)  # Возвращаемся в начало
            
            # Проверяем разделитель
            if ';' in first_line:
                delimiter = ';'
            else:
                delimiter = ','
            
            reader = csv.DictReader(file, delimiter=delimiter)
            
            for row in reader:
                # Извлекаем название и ID из разных возможных форматов
                name = row.get('Название точки', '').strip()
                id_2gis = row.get('ИД 2gist', '').strip()
                
                if name and id_2gis:
                    branches.append({
                        'name': name,
                        'id_2gis': id_2gis
                    })
                    
    except Exception as e:
        print(f"Ошибка при чтении CSV файла: {e}")
        return []
    
    return branches

def parse_all_branches(csv_path):
    """Парсинг отзывов для всех точек из CSV"""
    parser = TwoGISReviewsParser()
    branches = load_branches_from_csv(csv_path)
    
    if not branches:
        print("Не удалось загрузить данные из CSV файла")
        return
    
    print(f"Найдено {len(branches)} точек продаж")
    
    all_reviews = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Создаем директорию для результатов, если её нет
    os.makedirs('output', exist_ok=True)
    
    # Парсим отзывы для каждой точки
    for i, branch in enumerate(branches, 1):
        print(f"\n[{i}/{len(branches)}] Обработка: {branch['name']}")
        
        reviews = parser.parse_all_reviews(branch['id_2gis'], branch['name'])
        
        if reviews:
            all_reviews.extend(reviews)
            print(f"Получено {len(reviews)} отзывов")
        else:
            print(f"Не удалось получить отзывы для {branch['name']}")
        
        # Задержка между точками
        if i < len(branches):
            time.sleep(2)
    
    # Сохраняем все отзывы в один файл
    if all_reviews:
        # CSV
        csv_filename = f"output/all_reviews_{timestamp}.csv"
        fieldnames = [
            'branch_id', 'branch_name', 'review_id', 'user_name', 
            'rating', 'text', 'date_created', 'date_edited', 
            'is_verified', 'likes_count', 'comments_count'
        ]
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_reviews)
        
        # JSON
        json_filename = f"output/all_reviews_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(all_reviews, jsonfile, ensure_ascii=False, indent=2)
        
        # Статистика
        print(f"\n{'='*50}")
        print(f"ИТОГОВАЯ СТАТИСТИКА:")
        print(f"{'='*50}")
        print(f"Всего точек обработано: {len(branches)}")
        print(f"Всего отзывов собрано: {len(all_reviews)}")
        
        # Статистика по точкам
        branch_stats = {}
        for review in all_reviews:
            branch_name = review['branch_name']
            if branch_name not in branch_stats:
                branch_stats[branch_name] = {'count': 0, 'ratings': []}
            branch_stats[branch_name]['count'] += 1
            if review['rating']:
                branch_stats[branch_name]['ratings'].append(review['rating'])
        
        print(f"\nСтатистика по точкам:")
        for branch_name, stats in branch_stats.items():
            avg_rating = sum(stats['ratings']) / len(stats['ratings']) if stats['ratings'] else 0
            print(f"- {branch_name}: {stats['count']} отзывов, средний рейтинг: {avg_rating:.2f}")
        
        print(f"\nРезультаты сохранены в:")
        print(f"- {csv_filename}")
        print(f"- {json_filename}")
    else:
        print("\nНе удалось получить ни одного отзыва")

if __name__ == "__main__":
    # Путь к CSV файлу с точками продаж
    csv_path = "data/points.csv"  # Измените на путь к вашему файлу
    
    parse_all_branches(csv_path)
