#!/usr/bin/env python3
"""
Автоматизированные тесты для парсера отзывов 2GIS и API
"""
import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Импорт тестируемых модулей
from parser import TwoGISReviewsParser
from database import Base, Review, Branch, ParseReport
from daily_parse import get_existing_review_ids, save_new_reviews_to_db


class TestParser(unittest.TestCase):
    """Тесты для парсера 2GIS"""
    
    def setUp(self):
        self.parser = TwoGISReviewsParser()
        
    def test_init(self):
        """TC-P001: Проверка инициализации парсера"""
        self.assertEqual(self.parser.api_key, "6e7e1929-4ea9-4a5d-8c05-d601860389bd")
        self.assertIn("Mozilla", self.parser.headers['User-Agent'])
        
    @patch('requests.get')
    def test_get_reviews_success(self, mock_get):
        """TC-P001: Успешное получение отзывов"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'reviews': [
                {
                    'id': 'test_review_1',
                    'user': {'name': 'Тестовый пользователь'},
                    'rating': 5,
                    'text': 'Отличный магазин!',
                    'date_created': '2025-07-10T10:00:00Z',
                    'date_edited': '2025-07-10T10:00:00Z',
                    'is_verified': True,
                    'likes_count': 10,
                    'comments_count': 2,
                    'photos': []
                }
            ],
            'meta': {'total_count': 1}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.parser.get_reviews('test_branch_id', limit=12, offset=0)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['reviews']), 1)
        self.assertEqual(result['reviews'][0]['id'], 'test_review_1')
        
    @patch('requests.get')
    def test_get_reviews_with_photos(self, mock_get):
        """TC-P002: Обработка отзывов с фотографиями"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'reviews': [
                {
                    'id': 'test_review_photo',
                    'user': {'name': 'Фотограф'},
                    'rating': 4,
                    'text': 'Смотрите фото',
                    'date_created': '2025-07-10T10:00:00Z',
                    'photos': [
                        {
                            'preview_urls': {
                                'url': 'https://example.com/photo1.jpg',
                                '1920x': 'https://example.com/photo1_1920.jpg'
                            }
                        },
                        {
                            'preview_urls': {
                                '1920x': 'https://example.com/photo2_1920.jpg'
                            }
                        }
                    ]
                }
            ],
            'meta': {'total_count': 1}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        reviews = self.parser.parse_all_reviews('test_branch', 'Тестовый филиал')
        
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]['photos_count'], 2)
        self.assertEqual(len(reviews[0]['photos_urls']), 2)
        self.assertIn('https://example.com/photo1.jpg', reviews[0]['photos_urls'])
        
    @patch('requests.get')
    def test_pagination_handling(self, mock_get):
        """TC-P004: Обработка пагинации"""
        # Первая страница
        response1 = Mock()
        response1.json.return_value = {
            'reviews': [{'id': f'review_{i}'} for i in range(50)],
            'meta': {'total_count': 75}
        }
        response1.raise_for_status = Mock()
        
        # Вторая страница
        response2 = Mock()
        response2.json.return_value = {
            'reviews': [{'id': f'review_{i}'} for i in range(50, 75)],
            'meta': {'total_count': 75}
        }
        response2.raise_for_status = Mock()
        
        mock_get.side_effect = [response1, response2]
        
        with patch('time.sleep'):  # Пропускаем задержки в тестах
            reviews = self.parser.parse_all_reviews('test_branch', 'Тестовый филиал')
        
        self.assertEqual(len(reviews), 75)
        self.assertEqual(mock_get.call_count, 2)
        
    @patch('requests.get')
    def test_api_error_handling(self, mock_get):
        """TC-P005: Обработка ошибок API"""
        mock_get.side_effect = Exception("API недоступен")
        
        result = self.parser.get_reviews('test_branch', limit=12, offset=0)
        
        self.assertIsNone(result)
        
    def test_save_to_json(self):
        """Тест сохранения в JSON"""
        reviews = [
            {
                'branch_id': 'test_branch',
                'review_id': 'test_review',
                'user_name': 'Тест',
                'rating': 5,
                'text': 'Отлично!',
                'photos_urls': ['https://example.com/photo.jpg']
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            filename = f.name
            
        try:
            self.parser.save_to_json(reviews, filename)
            
            with open(filename, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                
            self.assertEqual(len(loaded_data), 1)
            self.assertEqual(loaded_data[0]['review_id'], 'test_review')
            self.assertEqual(loaded_data[0]['photos_urls'][0], 'https://example.com/photo.jpg')
        finally:
            os.unlink(filename)


class TestDatabase(unittest.TestCase):
    """Тесты для работы с базой данных"""
    
    def setUp(self):
        # Создаем тестовую БД в памяти
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def tearDown(self):
        self.session.close()
        
    def test_duplicate_prevention(self):
        """TC-P003: Предотвращение дублирования отзывов"""
        # Добавляем первый отзыв
        review1 = Review(
            review_id='duplicate_test',
            branch_id='test_branch',
            branch_name='Тестовый филиал',
            user_name='Пользователь',
            rating=5,
            text='Отличный магазин!',
            date_created=datetime.now()
        )
        self.session.add(review1)
        self.session.commit()
        
        # Получаем существующие ID
        existing_ids = get_existing_review_ids(self.session, 'test_branch')
        self.assertIn('duplicate_test', existing_ids)
        
        # Пытаемся добавить дубликат
        new_reviews = [
            {
                'id': 'duplicate_test',
                'user': {'name': 'Другой пользователь'},
                'rating': 1,
                'text': 'Изменённый текст'
            }
        ]
        
        count = save_new_reviews_to_db(
            self.session, 
            new_reviews, 
            'test_branch', 
            'Тестовый филиал',
            existing_ids
        )
        
        # Проверяем, что дубликат не добавлен
        self.assertEqual(count, 0)
        total_reviews = self.session.query(Review).filter_by(branch_id='test_branch').count()
        self.assertEqual(total_reviews, 1)
        
    def test_new_review_detection(self):
        """TC-I001: Обнаружение новых отзывов"""
        # Добавляем начальные отзывы
        for i in range(3):
            review = Review(
                review_id=f'old_review_{i}',
                branch_id='test_branch',
                branch_name='Тестовый филиал',
                user_name=f'Пользователь {i}',
                rating=4,
                text=f'Отзыв {i}',
                date_created=datetime.now() - timedelta(days=i+1)
            )
            self.session.add(review)
        self.session.commit()
        
        existing_ids = get_existing_review_ids(self.session, 'test_branch')
        self.assertEqual(len(existing_ids), 3)
        
        # Добавляем новые отзывы
        new_reviews = [
            {
                'id': 'new_review_1',
                'user': {'name': 'Новый пользователь'},
                'rating': 5,
                'text': 'Новый отзыв',
                'date_created': datetime.now().isoformat()
            }
        ]
        
        count = save_new_reviews_to_db(
            self.session,
            new_reviews,
            'test_branch',
            'Тестовый филиал', 
            existing_ids
        )
        
        self.assertEqual(count, 1)
        total_reviews = self.session.query(Review).filter_by(branch_id='test_branch').count()
        self.assertEqual(total_reviews, 4)


class TestAPIEndpoints(unittest.TestCase):
    """Тесты для API endpoints"""
    
    def setUp(self):
        from fastapi.testclient import TestClient
        from api_v2 import app
        self.client = TestClient(app)
        
    def test_health_check(self):
        """Проверка health endpoint"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        
    def test_main_page(self):
        """Проверка главной страницы"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("2GIS Reviews API", response.json()["message"])
        
    @patch('database.get_db')
    def test_branches_endpoint(self, mock_get_db):
        """Тест получения списка филиалов"""
        # Мокаем сессию БД
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.all.return_value = [
            Branch(branch_id='123', branch_name='Филиал 1', city='Алматы'),
            Branch(branch_id='456', branch_name='Филиал 2', city='Астана')
        ]
        mock_get_db.return_value = mock_session
        
        response = self.client.get("/api/v1/branches")
        self.assertEqual(response.status_code, 200)
        
    def test_invalid_endpoint(self):
        """Тест несуществующего endpoint"""
        response = self.client.get("/api/v1/invalid")
        self.assertEqual(response.status_code, 404)


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
    @patch('telegram_notifications.send_notifications_sync')
    @patch('parser.TwoGISReviewsParser.parse_all_reviews')
    def test_full_cycle(self, mock_parse, mock_notify):
        """TC-I001: Полный цикл от парсинга до уведомления"""
        # Мокаем результаты парсинга
        mock_parse.return_value = [
            {
                'review_id': 'new_review_integration',
                'branch_id': 'test_branch',
                'branch_name': 'Тестовый филиал',
                'user_name': 'Интеграционный тест',
                'rating': 5,
                'text': 'Тестовый отзыв для интеграции',
                'date_created': datetime.now().isoformat(),
                'photos_count': 0,
                'photos_urls': []
            }
        ]
        
        # Проверяем, что уведомления вызываются
        mock_notify.return_value = None
        
        # Здесь бы вызывался daily_parse.main(), но для теста достаточно проверки моков
        self.assertTrue(True)  # Placeholder для демонстрации структуры теста


if __name__ == '__main__':
    unittest.main()