import requests
import json

def test_api():
    """Тестирование API 2GIS с предоставленными параметрами"""
    
    # ID точки из примера
    branch_id = "70000001057699052"
    
    # URL и параметры
    url = f"https://public-api.reviews.2gis.com/2.0/branches/{branch_id}/reviews"
    
    params = {
        'is_advertiser': 'false',
        'fields': 'meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,reviews.hiding_reason,reviews.is_verified',
        'without_my_first_review': 'false',
        'rated': 'true',
        'sort_by': 'date_edited',
        'locale': 'ru_KZ',
        'key': '6e7e1929-4ea9-4a5d-8c05-d601860389bd',
        'limit': '12'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print("Отправка запроса к API 2GIS...")
    print(f"URL: {url}")
    print(f"Параметры: {json.dumps(params, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        print(f"\nСтатус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Выводим мета-информацию
            meta = data.get('meta', {})
            print(f"\nМета-информация:")
            print(f"- Общее количество отзывов: {meta.get('total_count', 0)}")
            print(f"- Рейтинг филиала: {meta.get('branch_rating', 'N/A')}")
            print(f"- Количество отзывов филиала: {meta.get('branch_reviews_count', 0)}")
            
            # Выводим информацию об отзывах
            reviews = data.get('reviews', [])
            print(f"\nПолучено отзывов: {len(reviews)}")
            
            if reviews:
                print("\nПример первого отзыва:")
                first_review = reviews[0]
                print(f"- ID: {first_review.get('id')}")
                print(f"- Пользователь: {first_review.get('user', {}).get('name', 'Аноним')}")
                print(f"- Рейтинг: {first_review.get('rating')}")
                print(f"- Текст: {first_review.get('text', '')[:100]}...")
                print(f"- Дата: {first_review.get('date_created')}")
                print(f"- Подтвержден: {first_review.get('is_verified', False)}")
            
            # Сохраняем полный ответ для анализа
            with open('output/test_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\nПолный ответ сохранен в output/test_response.json")
            
        else:
            print(f"Ошибка: {response.text}")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    test_api()
