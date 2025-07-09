#!/usr/bin/env python3
"""
Простой календарь для Telegram бота на русском языке
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, date
import calendar

MONTHS = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

def create_calendar(year: int, month: int) -> InlineKeyboardMarkup:
    """Создать календарь для выбора даты"""
    keyboard = []
    
    # Заголовок с месяцем и годом
    row = [
        InlineKeyboardButton("<", callback_data=f"calendar_prev_{year}_{month}"),
        InlineKeyboardButton(f"{MONTHS[month]} {year}", callback_data="calendar_ignore"),
        InlineKeyboardButton(">", callback_data=f"calendar_next_{year}_{month}")
    ]
    keyboard.append(row)
    
    # Дни недели
    row = []
    for day in DAYS:
        row.append(InlineKeyboardButton(day, callback_data="calendar_ignore"))
    keyboard.append(row)
    
    # Дни месяца
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="calendar_ignore"))
            else:
                row.append(InlineKeyboardButton(
                    str(day), 
                    callback_data=f"calendar_day_{year}_{month}_{day}"
                ))
        keyboard.append(row)
    
    # Кнопка отмены
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def process_calendar_selection(callback_data: str) -> tuple:
    """
    Обработать выбор в календаре
    Возвращает: (action, year, month, day)
    """
    parts = callback_data.split('_')
    
    if parts[0] != 'calendar':
        return None, None, None, None
    
    action = parts[1]
    
    if action == 'ignore':
        return 'ignore', None, None, None
    
    year = int(parts[2])
    month = int(parts[3])
    
    if action == 'day':
        day = int(parts[4])
        return 'day', year, month, day
    elif action in ['prev', 'next']:
        return action, year, month, None
    
    return None, None, None, None