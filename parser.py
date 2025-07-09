import requests
import json
import time
import csv
from datetime import datetime
import os

class TwoGISReviewsParser:
    def __init__(self):
        self.base_url = "https://public-api.reviews.2gis.com/2.0/branches/{}/reviews"
        self.api_key = "6e7e1929-4ea9-4a5d-8c05-d601860389bd"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def get_reviews(self, branch_id, limit=12, offset=0):
        """Получение отзывов для конкретной точки"""
        url = self.base_url.format(branch_id)
        
        params = {
            'is_advertiser': 'false',
            'fields': 'meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,reviews.hiding_reason,reviews.is_verified',
            'without_my_first_review': 'false',
            'rated': 'true',
            'sort_by': 'date_edited',
            'locale': 'ru_KZ',
            'key': self.api_key,
            'limit': limit,
            'offset': offset
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении отзывов для {branch_id}: {e}")
            return None
    
    def parse_all_reviews(self, branch_id, branch_name):
        """Парсинг всех отзывов для точки"""
        all_reviews = []
        offset = 0
        limit = 50  # Увеличиваем лимит для более быстрого парсинга
        
        while True:
            print(f"Получение отзывов для {branch_name} (offset: {offset})")
            data = self.get_reviews(branch_id, limit=limit, offset=offset)
            
            if not data:
                break
                
            reviews = data.get('reviews', [])
            if not reviews:
                break
                
            for review in reviews:
                parsed_review = {
                    'branch_id': branch_id,
                    'branch_name': branch_name,
                    'review_id': review.get('id'),
                    'user_name': review.get('user', {}).get('name', 'Аноним'),
                    'rating': review.get('rating'),
                    'text': review.get('text', ''),
                    'date_created': review.get('date_created'),
                    'date_edited': review.get('date_edited'),
                    'is_verified': review.get('is_verified', False),
                    'likes_count': review.get('likes_count', 0),
                    'comments_count': review.get('comments_count', 0)
                }
                all_reviews.append(parsed_review)
            
            # Проверяем, есть ли еще отзывы
            total_count = data.get('meta', {}).get('total_count', 0)
            if offset + limit >= total_count:
                break
                
            offset += limit
            time.sleep(1)  # Задержка между запросами
            
        return all_reviews
    
    def save_to_csv(self, reviews, filename):
        """Сохранение отзывов в CSV файл"""
        if not reviews:
            return
            
        fieldnames = [
            'branch_id', 'branch_name', 'review_id', 'user_name', 
            'rating', 'text', 'date_created', 'date_edited', 
            'is_verified', 'likes_count', 'comments_count'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reviews)
        
        print(f"Сохранено {len(reviews)} отзывов в {filename}")
    
    def save_to_json(self, reviews, filename):
        """Сохранение отзывов в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(reviews, jsonfile, ensure_ascii=False, indent=2)
        
        print(f"Сохранено {len(reviews)} отзывов в {filename}")

def main():
    parser = TwoGISReviewsParser()
    
    # Пример использования для одной точки
    branch_id = "70000001057699052"
    branch_name = "Тестовая точка"
    
    print(f"Начинаем парсинг отзывов для {branch_name}")
    reviews = parser.parse_all_reviews(branch_id, branch_name)
    
    if reviews:
        # Сохраняем в разных форматах
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"output/reviews_{branch_id}_{timestamp}.csv"
        json_filename = f"output/reviews_{branch_id}_{timestamp}.json"
        
        parser.save_to_csv(reviews, csv_filename)
        parser.save_to_json(reviews, json_filename)
        
        # Выводим статистику
        print(f"\nСтатистика:")
        print(f"Всего отзывов: {len(reviews)}")
        ratings = [r['rating'] for r in reviews if r['rating']]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            print(f"Средний рейтинг: {avg_rating:.2f}")
    else:
        print("Не удалось получить отзывы")

if __name__ == "__main__":
    main()
