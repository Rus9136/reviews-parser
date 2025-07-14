#!/usr/bin/env python3
"""
Модуль для генерации статистики и аналитики для Telegram-бота
"""
import os
import io
import matplotlib
matplotlib.use('Agg')  # Использовать backend без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from typing import List, Dict, Tuple, Optional
import tempfile

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from database import Review, Branch

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройка matplotlib для русского языка
plt.rcParams['font.family'] = ['DejaVu Sans']
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

class TelegramAnalytics:
    """Класс для генерации аналитики и графиков для Telegram-бота"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_reviews_for_period(self, branch_id: str, date_from: datetime, date_to: datetime) -> List[Review]:
        """Получить отзывы за период"""
        return self.db.query(Review).filter(
            and_(
                Review.branch_id == branch_id,
                Review.date_created >= date_from,
                Review.date_created <= date_to
            )
        ).order_by(Review.date_created).all()
    
    def calculate_statistics(self, reviews: List[Review]) -> Dict:
        """Вычислить основную статистику по отзывам"""
        if not reviews:
            return {
                'total_reviews': 0,
                'avg_rating': 0,
                'positive_count': 0,
                'neutral_count': 0,
                'negative_count': 0,
                'positive_percent': 0,
                'neutral_percent': 0,
                'negative_percent': 0,
                'with_photos': 0,
                'with_photos_percent': 0
            }
        
        total = len(reviews)
        avg_rating = sum(r.rating for r in reviews if r.rating) / len([r for r in reviews if r.rating])
        
        # Подсчет по категориям
        positive = len([r for r in reviews if r.rating and r.rating >= 4])
        neutral = len([r for r in reviews if r.rating and r.rating == 3])
        negative = len([r for r in reviews if r.rating and r.rating <= 2])
        
        with_photos = len([r for r in reviews if r.photos_urls and len(r.photos_urls) > 0])
        
        return {
            'total_reviews': total,
            'avg_rating': round(avg_rating, 2),
            'positive_count': positive,
            'neutral_count': neutral,
            'negative_count': negative,
            'positive_percent': round(positive / total * 100, 1),
            'neutral_percent': round(neutral / total * 100, 1),
            'negative_percent': round(negative / total * 100, 1),
            'with_photos': with_photos,
            'with_photos_percent': round(with_photos / total * 100, 1)
        }
    
    def generate_rating_dynamics_chart(self, reviews: List[Review], branch_name: str, 
                                     date_from: datetime, date_to: datetime) -> str:
        """Создать график динамики рейтинга"""
        if not reviews:
            return self._create_no_data_chart(f"Динамика рейтинга - {branch_name}")
        
        # Группировка по дням
        daily_ratings = defaultdict(list)
        for review in reviews:
            if review.rating and review.date_created:
                day = review.date_created.date()
                daily_ratings[day].append(review.rating)
        
        # Вычисление средних рейтингов по дням
        dates = []
        avg_ratings = []
        
        current_date = date_from.date()
        while current_date <= date_to.date():
            dates.append(current_date)
            if current_date in daily_ratings:
                avg_rating = sum(daily_ratings[current_date]) / len(daily_ratings[current_date])
                avg_ratings.append(avg_rating)
            else:
                avg_ratings.append(None)
            current_date += timedelta(days=1)
        
        # Создание графика
        plt.figure(figsize=(14, 8))
        
        # Фильтрация None значений для отображения
        filtered_dates = []
        filtered_ratings = []
        for date, rating in zip(dates, avg_ratings):
            if rating is not None:
                filtered_dates.append(date)
                filtered_ratings.append(rating)
        
        if filtered_dates:
            plt.plot(filtered_dates, filtered_ratings, marker='o', linewidth=2, markersize=6, color='#2E86AB')
            plt.fill_between(filtered_dates, filtered_ratings, alpha=0.3, color='#A23B72')
        
        # Настройка осей
        plt.title(f'Динамика среднего рейтинга\n{branch_name}', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Средний рейтинг', fontsize=12)
        plt.ylim(0.5, 5.5)
        
        # Форматирование оси дат
        ax = plt.gca()
        if len(dates) > 30:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        else:
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        
        plt.xticks(rotation=45)
        
        # Добавление горизонтальных линий для ориентиров
        plt.axhline(y=4, color='green', linestyle='--', alpha=0.5, label='Хорошо (4.0)')
        plt.axhline(y=3, color='orange', linestyle='--', alpha=0.5, label='Удовлетворительно (3.0)')
        plt.axhline(y=2, color='red', linestyle='--', alpha=0.5, label='Плохо (2.0)')
        
        plt.legend(loc='upper right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Сохранение в временный файл
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(temp_file.name, dpi=300, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def generate_reviews_count_chart(self, reviews: List[Review], branch_name: str, 
                                   date_from: datetime, date_to: datetime) -> str:
        """Создать график динамики количества отзывов"""
        if not reviews:
            return self._create_no_data_chart(f"Количество отзывов - {branch_name}")
        
        # Определение периода группировки
        period_days = (date_to.date() - date_from.date()).days
        
        if period_days <= 31:
            # Группировка по дням
            group_by = 'day'
            date_format = '%d.%m'
        elif period_days <= 93:
            # Группировка по неделям
            group_by = 'week'
            date_format = '%d.%m'
        else:
            # Группировка по месяцам
            group_by = 'month'
            date_format = '%m.%Y'
        
        # Группировка отзывов
        grouped_data = defaultdict(int)
        
        for review in reviews:
            if review.date_created:
                if group_by == 'day':
                    key = review.date_created.date()
                elif group_by == 'week':
                    # Начало недели (понедельник)
                    key = review.date_created.date() - timedelta(days=review.date_created.weekday())
                else:  # month
                    key = review.date_created.replace(day=1).date()
                
                grouped_data[key] += 1
        
        # Подготовка данных для графика
        dates = sorted(grouped_data.keys())
        counts = [grouped_data[date] for date in dates]
        
        # Создание графика
        plt.figure(figsize=(14, 8))
        
        bars = plt.bar(dates, counts, color='#F18F01', alpha=0.8, edgecolor='#C73E1D', linewidth=1)
        
        # Настройка графика
        plt.title(f'Динамика количества отзывов\n{branch_name}', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Период', fontsize=12)
        plt.ylabel('Количество отзывов', fontsize=12)
        
        # Добавление значений на столбцы
        for bar, count in zip(bars, counts):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    str(count), ha='center', va='bottom', fontweight='bold')
        
        # Форматирование оси дат
        ax = plt.gca()
        if group_by == 'day':
            ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
            if len(dates) > 20:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
        elif group_by == 'week':
            ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        else:  # month
            ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        # Сохранение в временный файл
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(temp_file.name, dpi=300, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def generate_rating_distribution_chart(self, reviews: List[Review], branch_name: str) -> str:
        """Создать круговую диаграмму распределения отзывов по рейтингам"""
        if not reviews:
            return self._create_no_data_chart(f"Распределение отзывов - {branch_name}")
        
        # Подсчет отзывов по категориям
        positive = len([r for r in reviews if r.rating and r.rating >= 4])
        neutral = len([r for r in reviews if r.rating and r.rating == 3])
        negative = len([r for r in reviews if r.rating and r.rating <= 2])
        
        if positive + neutral + negative == 0:
            return self._create_no_data_chart(f"Распределение отзывов - {branch_name}")
        
        # Данные для диаграммы
        sizes = [positive, neutral, negative]
        labels = ['Позитивные\n(4-5 звезд)', 'Нейтральные\n(3 звезды)', 'Негативные\n(1-2 звезды)']
        colors = ['#2E8B57', '#FFD700', '#DC143C']
        
        # Фильтрация пустых категорий
        filtered_sizes = []
        filtered_labels = []
        filtered_colors = []
        
        for size, label, color in zip(sizes, labels, colors):
            if size > 0:
                filtered_sizes.append(size)
                filtered_labels.append(label)
                filtered_colors.append(color)
        
        # Создание диаграммы
        plt.figure(figsize=(12, 10))
        
        wedges, texts, autotexts = plt.pie(filtered_sizes, labels=filtered_labels, colors=filtered_colors,
                                          autopct='%1.1f%%', startangle=90, textprops={'fontsize': 12})
        
        # Улучшение внешнего вида
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(14)
        
        plt.title(f'Распределение отзывов по рейтингам\n{branch_name}', 
                 fontsize=16, fontweight='bold', pad=20)
        
        # Добавление легенды с количеством
        legend_labels = []
        for i, (size, label) in enumerate(zip(filtered_sizes, filtered_labels)):
            percent = size / sum(filtered_sizes) * 100
            legend_labels.append(f'{label}: {size} ({percent:.1f}%)')
        
        plt.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0.5))
        
        plt.axis('equal')
        plt.tight_layout()
        
        # Сохранение в временный файл
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(temp_file.name, dpi=300, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def _create_no_data_chart(self, title: str) -> str:
        """Создать график с сообщением об отсутствии данных"""
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 'Нет данных для отображения', 
                ha='center', va='center', fontsize=20, 
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        
        # Сохранение в временный файл
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(temp_file.name, dpi=300, bbox_inches='tight')
        plt.close()
        
        return temp_file.name
    
    def generate_summary_text(self, reviews: List[Review], branch_name: str, 
                            date_from: datetime, date_to: datetime) -> str:
        """Создать текстовую сводку статистики"""
        if not reviews:
            return f"📊 Статистика для филиала '{branch_name}'\n" \
                   f"📅 Период: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}\n\n" \
                   f"❌ За выбранный период отзывов не найдено."
        
        stats = self.calculate_statistics(reviews)
        
        # Определение периода для сравнения (предыдущий период той же длительности)
        period_length = date_to - date_from
        previous_from = date_from - period_length
        previous_to = date_from - timedelta(days=1)
        
        previous_reviews = self.get_reviews_for_period(reviews[0].branch_id, previous_from, previous_to)
        previous_stats = self.calculate_statistics(previous_reviews)
        
        # Вычисление изменений
        count_change = stats['total_reviews'] - previous_stats['total_reviews']
        rating_change = stats['avg_rating'] - previous_stats['avg_rating']
        
        # Формирование текста
        summary = f"📊 Статистика для филиала '{branch_name}'\n"
        summary += f"📅 Период: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}\n\n"
        
        summary += f"📈 Общие показатели:\n"
        summary += f"• Всего отзывов: {stats['total_reviews']}"
        
        if count_change != 0:
            change_text = f"({count_change:+d} к предыдущему периоду)"
            summary += f" {change_text}"
        summary += "\n"
        
        summary += f"• Средний рейтинг: {stats['avg_rating']:.1f}/5"
        if abs(rating_change) >= 0.1:
            change_text = f"({rating_change:+.1f} к предыдущему периоду)"
            summary += f" {change_text}"
        summary += "\n"
        
        summary += f"• Отзывов с фотографиями: {stats['with_photos']} ({stats['with_photos_percent']:.1f}%)\n\n"
        
        summary += f"📋 Распределение по рейтингам:\n"
        summary += f"• Позитивные (4-5 ⭐): {stats['positive_count']} ({stats['positive_percent']:.1f}%)\n"
        summary += f"• Нейтральные (3 ⭐): {stats['neutral_count']} ({stats['neutral_percent']:.1f}%)\n"
        summary += f"• Негативные (1-2 ⭐): {stats['negative_count']} ({stats['negative_percent']:.1f}%)\n\n"
        
        # Добавление рекомендаций
        if stats['negative_percent'] > 20:
            summary += "⚠️ Рекомендация: Высокий процент негативных отзывов. Обратите внимание на качество обслуживания.\n"
        elif stats['positive_percent'] > 80:
            summary += "✅ Отлично: Высокий процент позитивных отзывов!\n"
        
        return summary
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """Очистить временные файлы"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Ошибка при удалении временного файла {file_path}: {e}")

def generate_analytics_report(db_session: Session, branch_id: str, branch_name: str,
                            date_from: datetime, date_to: datetime) -> Dict:
    """Основная функция для генерации полного отчета аналитики"""
    analytics = TelegramAnalytics(db_session)
    
    # Получение отзывов
    reviews = analytics.get_reviews_for_period(branch_id, date_from, date_to)
    
    # Генерация графиков
    rating_chart = analytics.generate_rating_dynamics_chart(reviews, branch_name, date_from, date_to)
    count_chart = analytics.generate_reviews_count_chart(reviews, branch_name, date_from, date_to)
    distribution_chart = analytics.generate_rating_distribution_chart(reviews, branch_name)
    
    # Генерация текстовой сводки
    summary = analytics.generate_summary_text(reviews, branch_name, date_from, date_to)
    
    return {
        'summary_text': summary,
        'rating_chart': rating_chart,
        'count_chart': count_chart,
        'distribution_chart': distribution_chart,
        'temp_files': [rating_chart, count_chart, distribution_chart]
    }