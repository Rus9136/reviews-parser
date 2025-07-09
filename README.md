# Парсер отзывов 2GIS

## Описание
Проект для парсинга отзывов с платформы 2GIS для точек продаж "Сандык Тары".

## Структура проекта
- `parser.py` - основной скрипт парсера
- `config.py` - конфигурация и настройки
- `data/` - директория для хранения данных
- `output/` - директория для результатов парсинга

## API Endpoint
```
GET https://public-api.reviews.2gis.com/2.0/branches/{branch_id}/reviews
```

## Параметры запроса
- `is_advertiser`: false
- `fields`: meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,reviews.hiding_reason,reviews.is_verified
- `without_my_first_review`: false
- `rated`: true
- `sort_by`: date_edited
- `locale`: ru_KZ
- `key`: 6e7e1929-4ea9-4a5d-8c05-d601860389bd
- `limit`: 12
