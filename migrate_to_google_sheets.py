#!/usr/bin/env python3
"""
Скрипт для переноса данных из CSV файла в Google Sheets
и добавления колонки id_iiko
"""

import csv
import gspread
from google.oauth2.service_account import Credentials
import sys
from typing import List, Dict

# Настройки
SPREADSHEET_ID = "13przZzgeCQay1dhunOuMtGc-_lV6y_xGrNOtCoG3ssQ"
CSV_FILE_PATH = "data/sandyq_tary_branches.csv"
SERVICE_ACCOUNT_FILE = "basic-zenith-465712-s5-63bf748b2e1c.json"

# Области доступа
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def read_csv_data(file_path: str) -> List[List[str]]:
    """Читает данные из CSV файла"""
    data = []
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            # Используем delimiter ';' так как в CSV разделитель - точка с запятой
            csv_reader = csv.reader(file, delimiter=';')
            
            for row in csv_reader:
                # Пропускаем пустые строки
                if any(cell.strip() for cell in row):
                    data.append(row)
                    
        print(f"Прочитано {len(data)} строк из CSV файла")
        return data
        
    except Exception as e:
        print(f"Ошибка при чтении CSV файла: {e}")
        sys.exit(1)


def authenticate_google_sheets():
    """Аутентификация в Google Sheets API"""
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, 
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        print("Успешная аутентификация в Google Sheets")
        return client
        
    except Exception as e:
        print(f"Ошибка аутентификации: {e}")
        sys.exit(1)


def migrate_to_google_sheets():
    """Основная функция миграции данных"""
    print("Начало миграции данных из CSV в Google Sheets...")
    
    # 1. Читаем данные из CSV
    csv_data = read_csv_data(CSV_FILE_PATH)
    
    if not csv_data:
        print("Нет данных для миграции")
        return
    
    # 2. Аутентификация в Google Sheets
    client = authenticate_google_sheets()
    
    try:
        # 3. Открываем таблицу
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.get_worksheet(0)  # Первый лист
        print(f"Открыта таблица: {spreadsheet.title}")
        
        # 4. Очищаем существующие данные
        worksheet.clear()
        print("Существующие данные очищены")
        
        # 5. Добавляем заголовки с новой колонкой id_iiko
        headers = csv_data[0] + ["id_iiko"]
        
        # 6. Подготавливаем данные для загрузки
        # Добавляем пустое значение для id_iiko к каждой строке данных
        data_to_upload = [headers]
        
        for row in csv_data[1:]:  # Пропускаем заголовки
            # Добавляем пустое значение для id_iiko
            row_with_iiko = row + [""]
            data_to_upload.append(row_with_iiko)
        
        # 7. Загружаем все данные одним запросом
        worksheet.update('A1', data_to_upload)
        print(f"Загружено {len(data_to_upload) - 1} строк данных (без заголовков)")
        
        # 8. Форматируем заголовки (жирный шрифт)
        worksheet.format('A1:D1', {
            "textFormat": {
                "bold": True
            }
        })
        
        # 9. Устанавливаем автоматический размер колонок
        worksheet.columns_auto_resize(0, len(headers) - 1)
        
        print("\nМиграция успешно завершена!")
        print(f"Добавлена новая колонка 'id_iiko' (пустая)")
        print(f"Всего колонок: {len(headers)}")
        print(f"Заголовки: {headers}")
        
    except Exception as e:
        print(f"Ошибка при работе с Google Sheets: {e}")
        sys.exit(1)


if __name__ == "__main__":
    migrate_to_google_sheets()