# 🚀 Быстрый старт - Аналитика Telegram-бота

## 📋 Что реализовано

✅ **Новый раздел "Статистика и аналитика"** в главном меню Telegram-бота  
✅ **3 типа визуальных графиков**:
- График динамики рейтинга (линейный)
- График количества отзывов (столбцы)
- Распределение по оценкам (круговая диаграмма)

✅ **Текстовые отчеты** с автоматическими рекомендациями  
✅ **Сравнение с предыдущими периодами**  
✅ **Интеграция с существующим календарем**  

## 🛠️ Установка

### 1. Установка зависимостей
```bash
source venv/bin/activate
pip install matplotlib
```

### 2. Файлы добавлены в проект:
- `telegram_analytics.py` - основной модуль
- `test_analytics.py` - тесты
- `test_telegram_analytics.py` - тесты интеграции
- `ANALYTICS_DOCUMENTATION.md` - полная документация

### 3. Перезапуск бота
```bash
systemctl restart telegram-bot.service
```

## 📱 Как использовать

### Пользовательский интерфейс:
1. **Откройте бота** → `/start`
2. **Нажмите "📈 Статистика и аналитика"** (новая кнопка)
3. **Выберите филиал** (если подписок несколько)
4. **Выберите даты** через календарь
5. **Получите отчет**:
   - Текстовую сводку
   - 3 графика как изображения
   - Рекомендации

### Пример отчета:
```
📊 Статистика для филиала 'Tary Аюсай'
📅 Период: 15.06.2025 - 14.07.2025

📈 Общие показатели:
• Всего отзывов: 169 (+7 к предыдущему периоду)
• Средний рейтинг: 4.3/5 (+0.2 к предыдущему периоду)
• Отзывов с фотографиями: 24 (14.2%)

📋 Распределение по рейтингам:
• Позитивные (4-5 ⭐): 136 (80.5%)
• Нейтральные (3 ⭐): 4 (2.4%)
• Негативные (1-2 ⭐): 29 (17.2%)

✅ Отлично: Высокий процент позитивных отзывов!
```

## 🧪 Тестирование

### Тест базового функционала:
```bash
source venv/bin/activate
python test_analytics.py
```

### Тест интеграции с ботом:
```bash
source venv/bin/activate
python test_telegram_analytics.py
```

### Ожидаемый результат:
```
🧪 Тестирование модуля аналитики...
✅ Найдено 169 отзывов за период 14.06.2025 - 14.07.2025
📊 Статистика: 169 отзывов, средний рейтинг 4.29
✅ Отчет сгенерирован: 3 графика созданы
✅ Тест успешно завершен!
```

## 🔧 Основные изменения в коде

### В `telegram_bot.py`:
- Добавлена кнопка "📈 Статистика и аналитика"
- Функция `show_analytics_menu()`
- Функция `show_analytics_for_period()`
- Обновлены обработчики календаря
- Обновлена справка

### В `requirements.txt`:
- Добавлен `matplotlib>=3.7.0`

## 📊 Характеристики графиков

### График рейтинга:
- **Тип**: Линейный с заливкой
- **Группировка**: По дням
- **Цвета**: Синий (#2E86AB) + розовая заливка
- **Особенности**: Опорные линии для оценок качества

### График количества:
- **Тип**: Столбцы
- **Группировка**: Дни/недели/месяцы (автоматически)
- **Цвет**: Оранжевый (#F18F01)
- **Особенности**: Значения на столбцах

### Распределение оценок:
- **Тип**: Круговая диаграмма
- **Категории**: Позитивные/Нейтральные/Негативные
- **Цвета**: Зеленый/Желтый/Красный
- **Особенности**: Проценты на диаграмме + легенда

## 🚨 Важные моменты

### Безопасность:
- Временные файлы создаются в `/tmp/` с уникальными именами
- Автоматическая очистка после отправки
- Проверка принадлежности филиала пользователю

### Производительность:
- Графики генерируются по запросу
- Автоматическая группировка для больших периодов
- Эффективные SQL-запросы

### Совместимость:
- Полная совместимость с существующими функциями
- Календарь работает для отзывов И аналитики
- Никаких изменений в базе данных

## 💡 Рекомендации для пользователей

### Оптимальные периоды:
- **7-14 дней**: Детальный анализ по дням
- **Месяц**: Анализ трендов по неделям
- **Квартал**: Долгосрочные тренды по месяцам

### Интерпретация результатов:
- **Позитивные >80%**: Отличная работа
- **Негативные >20%**: Требуется внимание
- **Рост рейтинга**: Улучшение качества
- **Снижение количества**: Возможные проблемы

---

🎯 **Готово к использованию!** Новый функционал полностью интегрирован и протестирован.