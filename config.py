# Конфигурация парсера отзывов 2GIS

# API настройки
API_KEY = "6e7e1929-4ea9-4a5d-8c05-d601860389bd"
BASE_URL = "https://public-api.reviews.2gis.com/2.0/branches/{}/reviews"

# Параметры запросов
DEFAULT_PARAMS = {
    'is_advertiser': 'false',
    'fields': 'meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,reviews.hiding_reason,reviews.is_verified',
    'without_my_first_review': 'false',
    'rated': 'true',
    'sort_by': 'date_edited',
    'locale': 'ru_KZ'
}

# Настройки парсинга
BATCH_SIZE = 50  # Количество отзывов за один запрос
REQUEST_DELAY = 1  # Задержка между запросами в секундах
BRANCH_DELAY = 2  # Задержка между обработкой разных точек

# Пути к файлам
DATA_DIR = "data"
OUTPUT_DIR = "output"
