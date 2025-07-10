"""
Менеджер кэширования для часто используемых данных
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class CacheManager:
    """Менеджер кэша для Reviews Parser API"""
    
    def __init__(self):
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Проверяем соединение
            self.redis_client.ping()
            logger.info(f"Подключение к Redis успешно: {redis_url}")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {str(e)}")
            self.redis_client = None
    
    def is_available(self) -> bool:
        """Проверка доступности кэша"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _make_key(self, prefix: str, *args) -> str:
        """Создание ключа для кэша"""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Получение данных из кэша"""
        if not self.is_available():
            return None
        
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Ошибка получения данных из кэша {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Сохранение данных в кэш"""
        if not self.is_available():
            return False
        
        try:
            data = json.dumps(value, ensure_ascii=False, default=str)
            self.redis_client.setex(key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения данных в кэш {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Удаление данных из кэша"""
        if not self.is_available():
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления данных из кэша {key}: {str(e)}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Удаление данных по шаблону"""
        if not self.is_available():
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Ошибка удаления данных по шаблону {pattern}: {str(e)}")
            return 0
    
    # Специфичные методы для Reviews Parser API
    
    def get_reviews_cache(self, branch_id: str, limit: int = 50, offset: int = 0) -> Optional[List[Dict]]:
        """Получение отзывов из кэша"""
        key = self._make_key('reviews', branch_id, limit, offset)
        return self.get(key)
    
    def set_reviews_cache(self, branch_id: str, reviews: List[Dict], limit: int = 50, offset: int = 0, ttl: int = 1800) -> bool:
        """Сохранение отзывов в кэш (30 минут)"""
        key = self._make_key('reviews', branch_id, limit, offset)
        return self.set(key, reviews, ttl)
    
    def get_branch_stats_cache(self, branch_id: str) -> Optional[Dict]:
        """Получение статистики филиала из кэша"""
        key = self._make_key('branch_stats', branch_id)
        return self.get(key)
    
    def set_branch_stats_cache(self, branch_id: str, stats: Dict, ttl: int = 3600) -> bool:
        """Сохранение статистики филиала в кэш (1 час)"""
        key = self._make_key('branch_stats', branch_id)
        return self.set(key, stats, ttl)
    
    def get_general_stats_cache(self) -> Optional[Dict]:
        """Получение общей статистики из кэша"""
        key = self._make_key('general_stats')
        return self.get(key)
    
    def set_general_stats_cache(self, stats: Dict, ttl: int = 1800) -> bool:
        """Сохранение общей статистики в кэш (30 минут)"""
        key = self._make_key('general_stats')
        return self.set(key, stats, ttl)
    
    def get_recent_reviews_cache(self, days: int = 7) -> Optional[List[Dict]]:
        """Получение недавних отзывов из кэша"""
        key = self._make_key('recent_reviews', days)
        return self.get(key)
    
    def set_recent_reviews_cache(self, reviews: List[Dict], days: int = 7, ttl: int = 900) -> bool:
        """Сохранение недавних отзывов в кэш (15 минут)"""
        key = self._make_key('recent_reviews', days)
        return self.set(key, reviews, ttl)
    
    def get_branches_list_cache(self) -> Optional[List[Dict]]:
        """Получение списка филиалов из кэша"""
        key = self._make_key('branches_list')
        return self.get(key)
    
    def set_branches_list_cache(self, branches: List[Dict], ttl: int = 7200) -> bool:
        """Сохранение списка филиалов в кэш (2 часа)"""
        key = self._make_key('branches_list')
        return self.set(key, branches, ttl)
    
    def invalidate_branch_cache(self, branch_id: str):
        """Инвалидация кэша для конкретного филиала"""
        patterns = [
            f'reviews:{branch_id}:*',
            f'branch_stats:{branch_id}',
            'general_stats',
            'recent_reviews:*'
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = self.delete_pattern(pattern)
            total_deleted += deleted
            logger.info(f"Инвалидирован кэш по шаблону {pattern}: {deleted} ключей")
        
        logger.info(f"Всего инвалидировано ключей для филиала {branch_id}: {total_deleted}")
    
    def invalidate_all_cache(self):
        """Инвалидация всего кэша"""
        patterns = [
            'reviews:*',
            'branch_stats:*',
            'general_stats',
            'recent_reviews:*',
            'branches_list'
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = self.delete_pattern(pattern)
            total_deleted += deleted
            logger.info(f"Инвалидирован кэш по шаблону {pattern}: {deleted} ключей")
        
        logger.info(f"Всего инвалидировано ключей: {total_deleted}")
    
    def get_cache_stats(self) -> Dict:
        """Получение статистики кэша"""
        if not self.is_available():
            return {"error": "Redis недоступен"}
        
        try:
            info = self.redis_client.info('memory')
            keyspace = self.redis_client.info('keyspace')
            
            # Подсчитываем ключи по типам
            patterns = {
                'reviews': 'reviews:*',
                'branch_stats': 'branch_stats:*',
                'general_stats': 'general_stats',
                'recent_reviews': 'recent_reviews:*',
                'branches_list': 'branches_list'
            }
            
            keys_count = {}
            for name, pattern in patterns.items():
                keys = self.redis_client.keys(pattern)
                keys_count[name] = len(keys)
            
            return {
                'memory_used': info.get('used_memory_human', 'N/A'),
                'memory_peak': info.get('used_memory_peak_human', 'N/A'),
                'keys_total': keyspace.get('db0', {}).get('keys', 0) if keyspace else 0,
                'keys_by_type': keys_count,
                'connected_clients': self.redis_client.info('clients').get('connected_clients', 0)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики кэша: {str(e)}")
            return {"error": str(e)}

# Глобальный экземпляр менеджера кэша
cache_manager = CacheManager()

def get_cache_manager() -> CacheManager:
    """Получение глобального менеджера кэша"""
    return cache_manager