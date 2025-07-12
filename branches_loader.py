#!/usr/bin/env python3
"""
Универсальный модуль для загрузки данных о филиалах из Google Sheets.
Заменяет функциональность загрузки из CSV файла.
"""

import os
import csv
import gspread
import logging
from typing import List, Dict, Optional
from google.oauth2.service_account import Credentials
from functools import lru_cache
import time
from datetime import datetime, timedelta

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация
SPREADSHEET_ID = "13przZzgeCQay1dhunOuMtGc-_lV6y_xGrNOtCoG3ssQ"
SERVICE_ACCOUNT_FILE = "basic-zenith-465712-s5-63bf748b2e1c.json"
CSV_FALLBACK_PATH = "data/sandyq_tary_branches.csv"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Кэш для хранения данных филиалов
_branches_cache = None
_cache_timestamp = None
_cache_ttl = 300  # 5 минут


class BranchesLoader:
    """Класс для загрузки данных о филиалах из Google Sheets с fallback на CSV"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Инициализация Google Sheets клиента"""
        try:
            if not os.path.exists(SERVICE_ACCOUNT_FILE):
                logger.warning(f"Файл ключа сервисного аккаунта не найден: {SERVICE_ACCOUNT_FILE}")
                return
                
            creds = Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=SCOPES
            )
            self.client = gspread.authorize(creds)
            logger.info("Google Sheets клиент успешно инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Google Sheets клиента: {e}")
            self.client = None
    
    def _load_from_google_sheets(self) -> List[Dict[str, str]]:
        """Загрузка данных из Google Sheets"""
        if not self.client:
            raise Exception("Google Sheets клиент не инициализирован")
        
        try:
            # Открываем таблицу
            spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.get_worksheet(0)  # Первый лист
            
            # Получаем все данные
            all_data = worksheet.get_all_records()
            
            branches = []
            for row in all_data:
                # Обрабатываем строку данных
                name = str(row.get('Название точки', '')).strip()
                id_2gis = str(row.get('ИД 2gist', '')).strip()
                id_steady = str(row.get('ИД steady', '')).strip()
                id_iiko = str(row.get('id_iiko', '')).strip()
                
                # Проверяем валидность данных
                if name and id_2gis and id_2gis.lower() not in ['', 'null', 'none']:
                    # Проверяем, что ID состоит из цифр
                    if id_2gis.isdigit():
                        branch_data = {
                            'name': name,
                            'id_2gis': id_2gis
                        }
                        
                        # Добавляем дополнительные поля если они есть
                        if id_steady and id_steady.lower() not in ['', 'null', 'none']:
                            branch_data['id_steady'] = id_steady
                        if id_iiko and id_iiko.lower() not in ['', 'null', 'none']:
                            branch_data['id_iiko'] = id_iiko
                            
                        branches.append(branch_data)
                    else:
                        logger.warning(f"Пропущена точка '{name}' - невалидный ID: {id_2gis}")
                else:
                    if name:
                        logger.warning(f"Пропущена точка '{name}' - отсутствует ID 2GIS")
            
            logger.info(f"Загружено {len(branches)} филиалов из Google Sheets")
            return branches
            
        except Exception as e:
            logger.error(f"Ошибка загрузки из Google Sheets: {e}")
            raise
    
    def _load_from_csv_fallback(self) -> List[Dict[str, str]]:
        """Загрузка данных из CSV файла как fallback"""
        if not os.path.exists(CSV_FALLBACK_PATH):
            raise FileNotFoundError(f"CSV файл не найден: {CSV_FALLBACK_PATH}")
        
        branches = []
        try:
            with open(CSV_FALLBACK_PATH, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file, delimiter=';')
                
                for row in reader:
                    # Ищем заголовки с учетом возможных кавычек
                    name_key = None
                    id_key = None
                    steady_key = None
                    
                    for key in row.keys():
                        if 'Название точки' in key:
                            name_key = key
                        elif 'ИД 2gist' in key:
                            id_key = key
                        elif 'ИД steady' in key:
                            steady_key = key
                    
                    if not name_key or not id_key:
                        continue
                        
                    name = row.get(name_key, '').strip()
                    id_2gis = row.get(id_key, '').strip()
                    id_steady = row.get(steady_key, '').strip() if steady_key else ''
                    
                    # Проверяем валидность ID
                    if name and id_2gis and id_2gis.lower() not in ['', 'null']:
                        if id_2gis.isdigit():
                            branch_data = {
                                'name': name,
                                'id_2gis': id_2gis
                            }
                            if id_steady and id_steady.lower() not in ['', 'null']:
                                branch_data['id_steady'] = id_steady
                            branches.append(branch_data)
                        else:
                            logger.warning(f"Пропущена точка '{name}' - невалидный ID: {id_2gis}")
                    else:
                        if name:
                            logger.warning(f"Пропущена точка '{name}' - отсутствует ID 2GIS")
            
            logger.info(f"Загружено {len(branches)} филиалов из CSV (fallback)")
            return branches
            
        except Exception as e:
            logger.error(f"Ошибка загрузки из CSV: {e}")
            raise
    
    def load_branches(self, use_cache: bool = True) -> List[Dict[str, str]]:
        """
        Загрузка филиалов с кэшированием и fallback на CSV
        
        Args:
            use_cache: Использовать кэш или загружать заново
            
        Returns:
            Список филиалов
        """
        global _branches_cache, _cache_timestamp
        
        # Проверяем кэш
        if use_cache and _branches_cache and _cache_timestamp:
            if datetime.now() - _cache_timestamp < timedelta(seconds=_cache_ttl):
                logger.debug("Используем кэшированные данные филиалов")
                return _branches_cache
        
        # Пытаемся загрузить из Google Sheets
        try:
            branches = self._load_from_google_sheets()
            
            # Обновляем кэш
            _branches_cache = branches
            _cache_timestamp = datetime.now()
            
            return branches
            
        except Exception as e:
            logger.warning(f"Не удалось загрузить из Google Sheets: {e}")
            logger.info("Переключаемся на CSV fallback")
            
            try:
                branches = self._load_from_csv_fallback()
                
                # Обновляем кэш (даже для fallback данных)
                _branches_cache = branches
                _cache_timestamp = datetime.now()
                
                return branches
                
            except Exception as csv_error:
                logger.error(f"Ошибка загрузки из CSV fallback: {csv_error}")
                
                # Если есть старые кэшированные данные, используем их
                if _branches_cache:
                    logger.warning("Используем устаревшие кэшированные данные")
                    return _branches_cache
                
                # Если ничего нет, выбрасываем исключение
                raise Exception(f"Не удалось загрузить данные ни из Google Sheets, ни из CSV: {e}")


# Глобальный экземпляр загрузчика
_loader = BranchesLoader()


def load_branches_from_csv(csv_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Совместимая функция для загрузки филиалов.
    Теперь использует Google Sheets вместо CSV файла.
    
    Args:
        csv_path: Путь к CSV файлу (игнорируется, оставлен для совместимости)
        
    Returns:
        Список филиалов в формате: [{'name': str, 'id_2gis': str, 'id_steady': str?}]
    """
    try:
        return _loader.load_branches()
    except Exception as e:
        logger.error(f"Критическая ошибка загрузки филиалов: {e}")
        # Возвращаем пустой список чтобы не ломать работу других компонентов
        return []


def reload_branches_cache():
    """Принудительно обновить кэш данных филиалов"""
    global _branches_cache, _cache_timestamp
    _branches_cache = None
    _cache_timestamp = None
    return _loader.load_branches(use_cache=False)


def get_branches_count() -> int:
    """Получить количество загруженных филиалов"""
    branches = load_branches_from_csv()
    return len(branches)


def get_branch_by_id(branch_id: str) -> Optional[Dict[str, str]]:
    """
    Найти филиал по ID 2GIS
    
    Args:
        branch_id: ID филиала в 2GIS
        
    Returns:
        Данные филиала или None если не найден
    """
    branches = load_branches_from_csv()
    for branch in branches:
        if branch.get('id_2gis') == branch_id:
            return branch
    return None


def get_branch_by_name(branch_name: str) -> Optional[Dict[str, str]]:
    """
    Найти филиал по названию
    
    Args:
        branch_name: Название филиала
        
    Returns:
        Данные филиала или None если не найден
    """
    branches = load_branches_from_csv()
    for branch in branches:
        if branch.get('name') == branch_name:
            return branch
    return None


if __name__ == "__main__":
    # Тестирование модуля
    logging.basicConfig(level=logging.INFO)
    
    print("🔄 Тестирование загрузчика филиалов...")
    
    try:
        branches = load_branches_from_csv()
        print(f"✅ Загружено {len(branches)} филиалов")
        
        if branches:
            print("\n📋 Первые 3 филиала:")
            for i, branch in enumerate(branches[:3]):
                print(f"  {i+1}. {branch['name']} (ID: {branch['id_2gis']})")
        
        # Тест поиска по ID
        if branches:
            test_id = branches[0]['id_2gis']
            found_branch = get_branch_by_id(test_id)
            if found_branch:
                print(f"\n🔍 Поиск по ID {test_id}: ✅ {found_branch['name']}")
            else:
                print(f"\n🔍 Поиск по ID {test_id}: ❌ Не найден")
                
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")