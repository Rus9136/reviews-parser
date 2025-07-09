#!/usr/bin/env python3
"""
Telegram Bot для уведомлений о новых отзывах
"""
import asyncio
import logging
import os
import csv
import time
from datetime import datetime, timedelta
from typing import List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.error import TelegramError

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from dotenv import load_dotenv

from database import SessionLocal, TelegramUser, TelegramSubscription, TelegramUserState, Review, Branch
from telegram_calendar import create_calendar, process_calendar_selection

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Глобальные переменные
user_states = {}  # Состояния пользователей для многошаговых команд

def get_db():
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass

def load_branches_from_csv():
    """Загрузить филиалы из CSV файла"""
    branches = []
    csv_path = "data/sandyq_tary_branches.csv"
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                # Обработка BOM и кавычек в названиях колонок
                branch_id = None
                branch_name = None
                
                for key, value in row.items():
                    if 'ИД 2gist' in key:
                        branch_id = value.strip() if value else ''
                    elif 'Название точки' in key:
                        branch_name = value.strip() if value else ''
                
                # Только филиалы с ID
                if branch_id and branch_id not in ['null', 'NULL', ''] and branch_name:
                    branches.append({
                        'id': branch_id,
                        'name': branch_name
                    })
                    
        logger.info(f"Загружено {len(branches)} филиалов из CSV")
        for branch in branches[:5]:  # Показать первые 5 филиалов в логах
            logger.info(f"  - {branch['name']} (ID: {branch['id']})")
    except Exception as e:
        logger.error(f"Ошибка при загрузке филиалов из CSV: {e}")
    
    return branches

def get_or_create_user(db: Session, user_id: str, user_data: dict) -> TelegramUser:
    """Получить или создать пользователя"""
    user = db.query(TelegramUser).filter(TelegramUser.user_id == user_id).first()
    
    if not user:
        user = TelegramUser(
            user_id=user_id,
            username=user_data.get('username'),
            first_name=user_data.get('first_name'),
            last_name=user_data.get('last_name'),
            language_code=user_data.get('language_code')
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Обновить данные пользователя
        user.username = user_data.get('username')
        user.first_name = user_data.get('first_name')
        user.last_name = user_data.get('last_name')
        user.language_code = user_data.get('language_code')
        user.updated_at = datetime.utcnow()
        db.commit()
    
    return user

def get_user_state(db: Session, user_id: str) -> dict:
    """Получить состояние пользователя из БД"""
    state_record = db.query(TelegramUserState).filter(TelegramUserState.user_id == user_id).first()
    if state_record and state_record.state_data:
        return state_record.state_data
    return {}

def save_user_state(db: Session, user_id: str, state_data: dict):
    """Сохранить состояние пользователя в БД"""
    state_record = db.query(TelegramUserState).filter(TelegramUserState.user_id == user_id).first()
    
    if state_record:
        state_record.state_data = state_data
        state_record.updated_at = datetime.utcnow()
    else:
        state_record = TelegramUserState(
            user_id=user_id,
            state_data=state_data
        )
        db.add(state_record)
    
    db.commit()

def clear_user_state(db: Session, user_id: str):
    """Очистить состояние пользователя"""
    state_record = db.query(TelegramUserState).filter(TelegramUserState.user_id == user_id).first()
    if state_record:
        db.delete(state_record)
        db.commit()

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message: bool = False):
    """Показать главное меню"""
    user_id = str(update.effective_user.id)
    
    # Проверить статус подписок
    db = get_db()
    try:
        subscriptions = db.query(TelegramSubscription).filter(
            and_(
                TelegramSubscription.user_id == user_id,
                TelegramSubscription.is_active == True
            )
        ).all()
        
        has_subscriptions = len(subscriptions) > 0
        
        keyboard = []
        
        if has_subscriptions:
            keyboard.append([InlineKeyboardButton("📊 Просмотр отзывов", callback_data="menu_reviews")])
            keyboard.append([InlineKeyboardButton("📝 Управление подписками", callback_data="menu_subscriptions")])
        else:
            keyboard.append([InlineKeyboardButton("🔔 Подписаться на уведомления", callback_data="menu_subscribe")])
        
        keyboard.append([InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if has_subscriptions:
            sub_names = [sub.branch_name for sub in subscriptions[:3]]
            sub_text = ", ".join(sub_names)
            if len(subscriptions) > 3:
                sub_text += f" и ещё {len(subscriptions) - 3}"
            
            text = f"🏪 Главное меню\n\n" \
                   f"✅ Вы подписаны на уведомления: {sub_text}\n\n" \
                   f"Выберите действие:"
        else:
            text = "🏪 Главное меню\n\n" \
                   "❌ У вас нет активных подписок\n\n" \
                   "Выберите действие:"
        
        if edit_message:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    finally:
        db.close()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = str(user.id)
    
    # Сохранить/обновить пользователя в БД
    db = get_db()
    try:
        user_data = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code
        }
        get_or_create_user(db, user_id, user_data)
    finally:
        db.close()
    
    # Показать главное меню
    await show_main_menu(update, context)

async def show_subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню подписок"""
    user_id = str(update.effective_user.id)
    
    # Загрузить филиалы
    branches = load_branches_from_csv()
    
    if not branches:
        await update.callback_query.edit_message_text(
            "❌ Не удалось загрузить список филиалов. Попробуйте позже."
        )
        return
    
    # Получить текущие подписки пользователя
    db = get_db()
    try:
        existing_subscriptions = db.query(TelegramSubscription).filter(
            and_(
                TelegramSubscription.user_id == user_id,
                TelegramSubscription.is_active == True
            )
        ).all()
        
        # Получить ID уже выбранных филиалов
        selected_branch_ids = [sub.branch_id for sub in existing_subscriptions]
        
        # Создать клавиатуру с филиалами
        keyboard = []
        
        # Добавить кнопку "Подписаться на все"
        all_selected = len(selected_branch_ids) == len(branches)
        if all_selected:
            keyboard.append([InlineKeyboardButton("❌ Отписаться от всех", callback_data="unselect_all_branches")])
        else:
            keyboard.append([InlineKeyboardButton("✅ Подписаться на все", callback_data="select_all_branches")])
        
        for branch in branches:
            is_selected = branch['id'] in selected_branch_ids
            text = f"✅ {branch['name']}" if is_selected else branch['name']
            keyboard.append([InlineKeyboardButton(
                text=text,
                callback_data=f"toggle_branch_{branch['id']}|{branch['name']}"
            )])
        
        keyboard.append([InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_selection")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Инициализировать состояние пользователя с существующими подписками
        state_data = {
            'selected_branches': selected_branch_ids,
            'available_branches': {b['id']: b['name'] for b in branches}
        }
        save_user_state(db, user_id, state_data)
        
        selected_count = len(selected_branch_ids)
        await update.callback_query.edit_message_text(
            f"🏪 Выберите филиалы для подписки на уведомления ({selected_count} выбрано):\n\n"
            "Нажмите на филиалы, которые вас интересуют, затем нажмите '✅ Подтвердить выбор'",
            reply_markup=reply_markup
        )
        
    finally:
        db.close()

async def show_subscriptions_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать управление подписками"""
    user_id = str(update.effective_user.id)
    
    db = get_db()
    try:
        subscriptions = db.query(TelegramSubscription).filter(
            and_(
                TelegramSubscription.user_id == user_id,
                TelegramSubscription.is_active == True
            )
        ).all()
        
        if not subscriptions:
            await update.callback_query.edit_message_text(
                "❌ У вас нет активных подписок.\n\n"
                "Используйте кнопку ниже для подписки на уведомления.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 Подписаться", callback_data="menu_subscribe")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ])
            )
            return
        
        keyboard = []
        keyboard.append([InlineKeyboardButton("➕ Добавить подписки", callback_data="menu_subscribe")])
        keyboard.append([InlineKeyboardButton("🗑 Отписаться от всех", callback_data="confirm_unsubscribe")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sub_list = "\n".join([f"• {sub.branch_name}" for sub in subscriptions])
        
        await update.callback_query.edit_message_text(
            f"📝 Управление подписками\n\n"
            f"✅ Ваши активные подписки:\n{sub_list}\n\n"
            f"Выберите действие:",
            reply_markup=reply_markup
        )
    
    finally:
        db.close()

async def show_reviews_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню просмотра отзывов"""
    user_id = str(update.effective_user.id)
    
    db = get_db()
    try:
        subscriptions = db.query(TelegramSubscription).filter(
            and_(
                TelegramSubscription.user_id == user_id,
                TelegramSubscription.is_active == True
            )
        ).all()
        
        if not subscriptions:
            await update.callback_query.edit_message_text(
                "❌ У вас нет активных подписок.\n\n"
                "Для просмотра отзывов сначала подпишитесь на филиалы.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔔 Подписаться", callback_data="menu_subscribe")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ])
            )
            return
        
        # Если только одна подписка, сразу переходим к выбору дат
        if len(subscriptions) == 1:
            branch_id = subscriptions[0].branch_id
            branch_name = subscriptions[0].branch_name
            
            state_data = {
                'action': 'reviews',
                'selected_branch_id': branch_id,
                'selected_branch_name': branch_name,
                'step': 'date_from'
            }
            save_user_state(db, user_id, state_data)
            
            # Создать календарь для выбора даты начала
            today = datetime.now()
            calendar = create_calendar(today.year, today.month)
            await update.callback_query.edit_message_text(
                f"📅 Выбран филиал: {branch_name}\n\n"
                f"Выберите дату начала периода:",
                reply_markup=calendar
            )
            
        else:
            # Создать клавиатуру с филиалами
            keyboard = []
            for sub in subscriptions:
                keyboard.append([InlineKeyboardButton(
                    text=sub.branch_name,
                    callback_data=f"reviews_{sub.branch_id}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "🏪 Выберите филиал для просмотра отзывов:",
                reply_markup=reply_markup
            )
    
    finally:
        db.close()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    await query.answer()
    
    # Получить состояние пользователя из БД
    db = get_db()
    try:
        data = query.data
        
        # Обработка календаря
        if data.startswith('calendar_'):
            action, year, month, day = process_calendar_selection(data)
            
            if action == 'ignore':
                # Игнорировать нажатие
                return
            
            user_state = get_user_state(db, user_id)
            if not user_state or user_state.get('action') != 'reviews':
                await query.edit_message_text("❌ Сессия истекла. Используйте /start для начала.")
                return
            
            if action in ['prev', 'next']:
                # Переключение месяца
                if action == 'prev':
                    month -= 1
                    if month < 1:
                        month = 12
                        year -= 1
                else:  # next
                    month += 1
                    if month > 12:
                        month = 1
                        year += 1
                
                calendar = create_calendar(year, month)
                branch_name = user_state.get('selected_branch_name', '')
                
                if user_state.get('step') == 'date_from':
                    await query.edit_message_text(
                        f"📅 Выбран филиал: {branch_name}\n\n"
                        f"Выберите дату начала периода:",
                        reply_markup=calendar
                    )
                elif user_state.get('step') == 'date_to':
                    date_from = datetime.fromisoformat(user_state['date_from']).date()
                    await query.edit_message_text(
                        f"📅 Дата начала: {date_from.strftime('%d.%m.%Y')}\n\n"
                        f"Теперь выберите дату окончания периода:",
                        reply_markup=calendar
                    )
                return
            
            elif action == 'day':
                # День выбран
                selected_date = datetime(year, month, day).date()
                
                if user_state.get('step') == 'date_from':
                    # Сохранить дату начала
                    user_state['date_from'] = selected_date.isoformat()
                    user_state['step'] = 'date_to'
                    save_user_state(db, user_id, user_state)
                    
                    # Показать календарь для выбора даты окончания
                    calendar = create_calendar(selected_date.year, selected_date.month)
                    await query.edit_message_text(
                        f"📅 Дата начала: {selected_date.strftime('%d.%m.%Y')}\n\n"
                        f"Теперь выберите дату окончания периода:",
                        reply_markup=calendar
                    )
                    return
                    
                elif user_state.get('step') == 'date_to':
                    # Проверить и сохранить дату окончания
                    date_from = datetime.fromisoformat(user_state['date_from']).date()
                    date_to = selected_date
                    
                    if date_to < date_from:
                        # Показать ошибку и календарь заново
                        calendar = create_calendar(year, month)
                        await query.edit_message_text(
                            f"❌ Дата окончания не может быть раньше даты начала!\n\n"
                            f"📅 Дата начала: {date_from.strftime('%d.%m.%Y')}\n\n"
                            f"Выберите дату окончания периода:",
                            reply_markup=calendar
                        )
                        return
                    
                    user_state['date_to'] = date_to.isoformat()
                    user_state['step'] = 'show_reviews'
                    user_state['offset'] = 0
                    save_user_state(db, user_id, user_state)
                    
                    # Показать отзывы
                    await show_reviews_for_period(query, context)
                    return
        
        # Обработка команд главного меню
        if data == "main_menu":
            await show_main_menu(update, context, edit_message=True)
            return
        elif data == "menu_subscribe":
            await show_subscription_menu(update, context)
            return
        elif data == "menu_subscriptions":
            await show_subscriptions_management(update, context)
            return
        elif data == "menu_reviews":
            await show_reviews_menu(update, context)
            return
        elif data == "menu_help":
            await query.edit_message_text(
                "ℹ️ Справка по боту\n\n"
                "🔔 Подписка на уведомления:\n"
                "• Выберите филиалы для получения уведомлений о новых отзывах\n"
                "• Уведомления приходят в реальном времени\n\n"
                "📊 Просмотр отзывов:\n"
                "• Просмотр отзывов за выбранный период\n"
                "• Отзывы отображаются по 5 штук\n\n"
                "📝 Управление подписками:\n"
                "• Добавление новых подписок\n"
                "• Отписка от всех уведомлений\n\n"
                "❓ Используйте /start для возврата в главное меню",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
                ])
            )
            return
        elif data == "confirm_unsubscribe":
            # Подтверждение отписки
            await query.edit_message_text(
                "⚠️ Вы действительно хотите отписаться от всех уведомлений?\n\n"
                "Это действие нельзя будет отменить.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да, отписаться", callback_data="do_unsubscribe")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="menu_subscriptions")]
                ])
            )
            return
        elif data == "do_unsubscribe":
            # Выполнить отписку
            try:
                # Деактивировать все подписки
                subscriptions = db.query(TelegramSubscription).filter(
                    and_(
                        TelegramSubscription.user_id == user_id,
                        TelegramSubscription.is_active == True
                    )
                ).all()
                
                for subscription in subscriptions:
                    subscription.is_active = False
                    subscription.updated_at = datetime.utcnow()
                
                db.commit()
                
                await query.edit_message_text(
                    "✅ Отписка выполнена!\n\n"
                    "Вы больше не будете получать уведомления о новых отзывах.\n\n"
                    "Используйте кнопку ниже для новой подписки.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔔 Подписаться", callback_data="menu_subscribe")],
                        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
                    ])
                )
                
            except Exception as e:
                logger.error(f"Ошибка при отписке: {e}")
                await query.edit_message_text(
                    "❌ Произошла ошибка при отписке. Попробуйте позже.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="menu_subscriptions")]
                    ])
                )
            return
        
        # Для команд, которые требуют состояние пользователя
        if data.startswith("toggle_branch_") or data.startswith("reviews_") or data == "show_more_reviews" or data == "confirm_selection" or data == "select_all_branches" or data == "unselect_all_branches":
            user_state = get_user_state(db, user_id)
            
            if not user_state:
                # Для команд связанных с подписками, попробуем восстановить состояние
                if data in ["select_all_branches", "unselect_all_branches"] or data.startswith("toggle_branch_"):
                    # Загрузить филиалы и создать новое состояние
                    branches = load_branches_from_csv()
                    if branches:
                        # Получить текущие подписки
                        existing_subscriptions = db.query(TelegramSubscription).filter(
                            and_(
                                TelegramSubscription.user_id == user_id,
                                TelegramSubscription.is_active == True
                            )
                        ).all()
                        selected_branch_ids = [sub.branch_id for sub in existing_subscriptions]
                        
                        user_state = {
                            'selected_branches': selected_branch_ids,
                            'available_branches': {b['id']: b['name'] for b in branches}
                        }
                        save_user_state(db, user_id, user_state)
                    else:
                        await query.edit_message_text("❌ Ошибка загрузки данных. Используйте /start для начала.")
                        return
                elif data.startswith("reviews_"):
                    # Для команды выбора филиала для просмотра отзывов
                    # Не требует предварительного состояния, создаем новое
                    pass  # Обработается ниже
                else:
                    await query.edit_message_text("❌ Сессия истекла. Используйте /start для начала.")
                    return
        
        if data.startswith("toggle_branch_"):
            # Переключить выбор филиала
            parts = data.split("_", 2)
            if len(parts) >= 3:
                branch_part = parts[2]  # "branch_id|branch_name"
                if '|' in branch_part:
                    branch_id, branch_name = branch_part.split('|', 1)
                else:
                    branch_id = branch_part
                    branch_name = 'Unknown'
                
                selected_branches = user_state.get('selected_branches', [])
                
                if branch_id in selected_branches:
                    selected_branches.remove(branch_id)
                else:
                    selected_branches.append(branch_id)
                
                user_state['selected_branches'] = selected_branches
                save_user_state(db, user_id, user_state)
                
                # Обновить клавиатуру
                keyboard = []
                
                # Добавить кнопку "Подписаться на все" / "Отписаться от всех"
                total_branches = len(user_state['available_branches'])
                all_selected = len(selected_branches) == total_branches
                if all_selected:
                    keyboard.append([InlineKeyboardButton("❌ Отписаться от всех", callback_data="unselect_all_branches")])
                else:
                    keyboard.append([InlineKeyboardButton("✅ Подписаться на все", callback_data="select_all_branches")])
                
                for bid, bname in user_state['available_branches'].items():
                    is_selected = bid in selected_branches
                    text = f"✅ {bname}" if is_selected else bname
                    keyboard.append([InlineKeyboardButton(
                        text=text,
                        callback_data=f"toggle_branch_{bid}|{bname}"
                    )])
                
                keyboard.append([InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_selection")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                selected_count = len(selected_branches)
                text = f"🏪 Выберите филиалы для подписки ({selected_count} выбрано):\n\n"
                text += "Нажмите на филиалы, которые вас интересуют, затем нажмите '✅ Подтвердить выбор'"
                
                await query.edit_message_text(text, reply_markup=reply_markup)
        
        elif data == "select_all_branches":
            # Выбрать все филиалы
            if user_state:
                # Выбрать все доступные филиалы
                all_branch_ids = list(user_state['available_branches'].keys())
                user_state['selected_branches'] = all_branch_ids
                save_user_state(db, user_id, user_state)
                
                # Обновить клавиатуру
                keyboard = []
                
                # Кнопка "Отписаться от всех" (все выбраны)
                keyboard.append([InlineKeyboardButton("❌ Отписаться от всех", callback_data="unselect_all_branches")])
                
                for bid, bname in user_state['available_branches'].items():
                    text = f"✅ {bname}"  # Все выбраны
                    keyboard.append([InlineKeyboardButton(
                        text=text,
                        callback_data=f"toggle_branch_{bid}|{bname}"
                    )])
                
                keyboard.append([InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_selection")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                selected_count = len(all_branch_ids)
                text = f"🏪 Выберите филиалы для подписки на уведомления ({selected_count} выбрано):\n\n"
                text += "Нажмите на филиалы, которые вас интересуют, затем нажмите '✅ Подтвердить выбор'"
                
                await query.edit_message_text(text, reply_markup=reply_markup)
        
        elif data == "unselect_all_branches":
            # Отменить выбор всех филиалов
            if user_state:
                user_state['selected_branches'] = []
                save_user_state(db, user_id, user_state)
                
                # Обновить клавиатуру
                keyboard = []
                
                # Кнопка "Подписаться на все" (ничего не выбрано)
                keyboard.append([InlineKeyboardButton("✅ Подписаться на все", callback_data="select_all_branches")])
                
                for bid, bname in user_state['available_branches'].items():
                    text = bname  # Ничего не выбрано
                    keyboard.append([InlineKeyboardButton(
                        text=text,
                        callback_data=f"toggle_branch_{bid}|{bname}"
                    )])
                
                keyboard.append([InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_selection")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                text = f"🏪 Выберите филиалы для подписки на уведомления (0 выбрано):\n\n"
                text += "Нажмите на филиалы, которые вас интересуют, затем нажмите '✅ Подтвердить выбор'"
                
                await query.edit_message_text(text, reply_markup=reply_markup)
        
        elif data.startswith("reviews_"):
            # Выбрать филиал для просмотра отзывов
            branch_id = data.replace("reviews_", "")
            
            # Получить название филиала из подписок
            subscription = db.query(TelegramSubscription).filter(
                and_(
                    TelegramSubscription.user_id == user_id,
                    TelegramSubscription.branch_id == branch_id,
                    TelegramSubscription.is_active == True
                )
            ).first()
            
            if subscription:
                branch_name = subscription.branch_name
                
                state_data = {
                    'action': 'reviews',
                    'selected_branch_id': branch_id,
                    'selected_branch_name': branch_name,
                    'step': 'date_from'
                }
                save_user_state(db, user_id, state_data)
                
                # Создать календарь для выбора даты начала
                today = datetime.now()
                calendar = create_calendar(today.year, today.month)
                await query.edit_message_text(
                    f"📅 Выбран филиал: {branch_name}\n\n"
                    f"Выберите дату начала периода:",
                    reply_markup=calendar
                )
            else:
                await query.edit_message_text(
                    "❌ Филиал не найден. Вернитесь в главное меню.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
                    ])
                )
        
        elif data == "show_more_reviews":
            # Показать еще отзывы
            if user_state and user_state.get('step') == 'show_reviews':
                user_state['offset'] = user_state.get('offset', 0) + 5
                save_user_state(db, user_id, user_state)
                await show_reviews_for_period(query, None)
        
        elif data == "confirm_selection":
            # Подтвердить выбор филиалов
            if not user_state:
                await query.edit_message_text("❌ Сессия истекла. Используйте /start для начала.")
                return
                
            selected_branches = user_state.get('selected_branches', [])
            
            if not selected_branches:
                await query.edit_message_text("❌ Вы не выбрали ни одного филиала. Используйте /start для начала.")
                return
            
            # Сохранить подписки в БД
            try:
                # Получить существующие подписки
                existing_subscriptions = db.query(TelegramSubscription).filter(
                    TelegramSubscription.user_id == user_id
                ).all()
                
                existing_branch_ids = [sub.branch_id for sub in existing_subscriptions]
                
                # Деактивировать подписки которые сняли
                for subscription in existing_subscriptions:
                    if subscription.branch_id not in selected_branches:
                        subscription.is_active = False
                        subscription.updated_at = datetime.utcnow()
                    elif not subscription.is_active:
                        # Реактивировать если была неактивной
                        subscription.is_active = True
                        subscription.updated_at = datetime.utcnow()
                
                # Добавить новые подписки
                for branch_id in selected_branches:
                    if branch_id not in existing_branch_ids:
                        branch_name = user_state['available_branches'].get(branch_id, 'Unknown')
                        subscription = TelegramSubscription(
                            user_id=user_id,
                            branch_id=branch_id,
                            branch_name=branch_name
                        )
                        db.add(subscription)
                
                db.commit()
                
                # Создать текст с выбранными филиалами
                selected_names = [user_state['available_branches'][bid] for bid in selected_branches]
                selected_text = "\n".join([f"• {name}" for name in selected_names])
                
                await query.edit_message_text(
                    f"✅ Подписка настроена!\n\n"
                    f"Вы будете получать уведомления о новых отзывах для:\n\n"
                    f"{selected_text}\n\n"
                    f"Теперь вы можете просматривать отзывы и управлять подписками.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 Просмотр отзывов", callback_data="menu_reviews")],
                        [InlineKeyboardButton("📝 Управление подписками", callback_data="menu_subscriptions")],
                        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
                    ])
                )
                
            except Exception as e:
                logger.error(f"Ошибка при сохранении подписок: {e}")
                await query.edit_message_text("❌ Произошла ошибка при сохранении подписок. Попробуйте позже.")
            
            # Очистить состояние пользователя
            clear_user_state(db, user_id)
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка в обработчике кнопок: {error_msg}")
        
        # Специальная обработка для различных типов ошибок
        if "Button_data_invalid" in error_msg or "Message is not modified" in error_msg:
            # Очистить состояние пользователя и предложить начать заново
            try:
                clear_user_state(db, user_id)
                await query.edit_message_text(
                    "⚠️ Состояние сессии нарушено. Пожалуйста, начните заново.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Начать заново", callback_data="main_menu")]
                    ])
                )
            except:
                await query.message.reply_text(
                    "⚠️ Произошла ошибка. Используйте /start для перезапуска.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Начать заново", callback_data="main_menu")]
                    ])
                )
        else:
            try:
                await query.edit_message_text(
                    "❌ Произошла ошибка. Попробуйте позже.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Попробовать снова", callback_data="main_menu")]
                    ])
                )
            except:
                await query.message.reply_text("❌ Произошла ошибка. Используйте /start для перезапуска.")
    finally:
        db.close()

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /unsubscribe - показывает главное меню"""
    await show_main_menu(update, context)

async def reviews_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /reviews - показывает главное меню"""
    await show_main_menu(update, context)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    db = get_db()
    try:
        user_state = get_user_state(db, user_id)
        
        if not user_state:
            return
    
        # Обработка дат теперь через календарь, а не текстовые сообщения
        if user_state.get('action') == 'reviews' and (user_state.get('step') == 'date_from' or user_state.get('step') == 'date_to'):
            # Игнорировать текстовые сообщения при выборе дат
            await update.message.reply_text(
                "📅 Пожалуйста, используйте календарь для выбора даты.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
                ])
            )
            return
    
    finally:
        db.close()

async def show_reviews_for_period(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    """Показать отзывы за период"""
    if hasattr(update_or_query, 'effective_user'):
        user_id = str(update_or_query.effective_user.id)
        is_callback = False
    else:
        user_id = str(update_or_query.from_user.id)
        is_callback = True
    
    db = get_db()
    try:
        user_state = get_user_state(db, user_id)
        
        if not user_state:
            return
        
        branch_id = user_state['selected_branch_id']
        branch_name = user_state['selected_branch_name']
        date_from = datetime.fromisoformat(user_state['date_from']).date()
        date_to = datetime.fromisoformat(user_state['date_to']).date()
        offset = user_state.get('offset', 0)
        limit = 5  # Показывать по 5 отзывов за раз
        # Получить отзывы за период
        reviews = db.query(Review).filter(
            and_(
                Review.branch_id == branch_id,
                Review.date_created >= datetime.combine(date_from, datetime.min.time()),
                Review.date_created <= datetime.combine(date_to, datetime.max.time())
            )
        ).order_by(desc(Review.date_created)).offset(offset).limit(limit + 1).all()
        
        if not reviews:
            if offset == 0:
                message = f"❌ Отзывов для филиала '{branch_name}' за период {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')} не найдено."
                # Добавить кнопку "Назад" для выбора другого периода
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Выбрать другой период", callback_data=f"reviews_{branch_id}")]
                ])
            else:
                message = "❌ Больше отзывов нет."
                # Добавить кнопку "Назад" для выбора другого периода
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Выбрать другой период", callback_data=f"reviews_{branch_id}")]
                ])
            
            if is_callback:
                await update_or_query.edit_message_text(message, reply_markup=keyboard)
            else:
                await update_or_query.message.reply_text(message, reply_markup=keyboard)
            
            # Очистить состояние
            clear_user_state(db, user_id)
            return
        
        # Показать отзывы (до 5 штук)
        reviews_to_show = reviews[:limit]
        has_more = len(reviews) > limit
        
        if offset == 0:
            header = f"📋 Отзывы для филиала '{branch_name}'\n"
            header += f"📅 Период: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}\n\n"
            if is_callback:
                await update_or_query.edit_message_text(header)
            else:
                await update_or_query.message.reply_text(header)
        
        for review in reviews_to_show:
            await send_review_message(update_or_query, review, show_branch=False)
            await asyncio.sleep(0.1)  # Небольшая задержка между сообщениями
        
        # Показать кнопку "Показать ещё" если есть ещё отзывы
        if has_more:
            keyboard = [
                [InlineKeyboardButton("📄 Показать ещё", callback_data="show_more_reviews")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if is_callback:
                await update_or_query.message.reply_text(
                    f"Показано {offset + len(reviews_to_show)} отзывов",
                    reply_markup=reply_markup
                )
            else:
                await update_or_query.message.reply_text(
                    f"Показано {offset + len(reviews_to_show)} отзывов",
                    reply_markup=reply_markup
                )
        else:
            message = "✅ Все отзывы за период показаны."
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if is_callback:
                await update_or_query.message.reply_text(message, reply_markup=reply_markup)
            else:
                await update_or_query.message.reply_text(message, reply_markup=reply_markup)
            # Очистить состояние
            clear_user_state(db, user_id)
    
    except Exception as e:
        logger.error(f"Ошибка при получении отзывов: {e}")
        if hasattr(update_or_query, 'message'):
            await update_or_query.message.reply_text("❌ Произошла ошибка при получении отзывов.")
        else:
            await update_or_query.edit_message_text("❌ Произошла ошибка при получении отзывов.")
    finally:
        db.close()

async def send_review_message(update_or_context, review: Review, show_branch: bool = True):
    """Отправить сообщение с отзывом"""
    # Форматирование отзыва
    rating_stars = "⭐" * int(review.rating) if review.rating else "⭐"
    
    message_text = ""
    if show_branch:
        message_text += f"📢 Новый отзыв для филиала {review.branch_name}:\n"
    
    message_text += f"👤 Автор: {review.user_name or 'Аноним'}\n"
    message_text += f"⭐ Рейтинг: {rating_stars} ({review.rating}/5)\n"
    message_text += f"📝 Текст: {review.text or 'Без текста'}\n"
    message_text += f"📅 Дата: {review.date_created.strftime('%d.%m.%Y %H:%M') if review.date_created else 'Неизвестно'}\n"
    
    # Определить способ отправки сообщения
    if hasattr(update_or_context, 'message'):
        # Обычное сообщение
        send_photo = update_or_context.message.reply_photo
        send_text = update_or_context.message.reply_text
        send_media_group = update_or_context.message.reply_media_group
    elif hasattr(update_or_context, 'bot'):
        # Контекст для уведомлений
        send_photo = lambda **kwargs: update_or_context.bot.send_photo(chat_id=update_or_context.chat_id, **kwargs)
        send_text = lambda **kwargs: update_or_context.bot.send_message(chat_id=update_or_context.chat_id, **kwargs)
        send_media_group = lambda **kwargs: update_or_context.bot.send_media_group(chat_id=update_or_context.chat_id, **kwargs)
    else:
        # Колбэк запрос
        send_photo = lambda **kwargs: update_or_context.message.reply_photo(**kwargs)
        send_text = lambda **kwargs: update_or_context.message.reply_text(**kwargs)
        send_media_group = lambda **kwargs: update_or_context.message.reply_media_group(**kwargs)
    
    # Отправка фотографий если есть
    if review.photos_urls and len(review.photos_urls) > 0:
        photos = review.photos_urls[:10]  # Максимум 10 фотографий
        
        if len(photos) == 1:
            # Одна фотография
            try:
                await send_photo(photo=photos[0], caption=message_text)
            except Exception as e:
                logger.error(f"Ошибка при отправке фото: {e}")
                # Отправить как текст если фото не получилось
                await send_text(text=message_text)
        else:
            # Несколько фотографий - альбом
            try:
                media = []
                for i, photo_url in enumerate(photos):
                    if i == 0:
                        media.append(InputMediaPhoto(media=photo_url, caption=message_text))
                    else:
                        media.append(InputMediaPhoto(media=photo_url))
                
                await send_media_group(media=media)
            except Exception as e:
                logger.error(f"Ошибка при отправке альбома: {e}")
                # Отправить как текст если альбом не получилось
                await send_text(text=message_text)
    else:
        # Без фотографий
        await send_text(text=message_text)

async def send_new_review_notifications(application):
    """Отправить уведомления о новых отзывах"""
    logger.info("Проверка новых отзывов для уведомлений...")
    
    db = get_db()
    try:
        # Получить неотправленные отзывы
        new_reviews = db.query(Review).filter(
            Review.sent_to_telegram == False
        ).all()
        
        if not new_reviews:
            logger.info("Новых отзывов нет")
            return
        
        logger.info(f"Найдено {len(new_reviews)} новых отзывов")
        
        # Получить все активные подписки
        subscriptions = db.query(TelegramSubscription).filter(
            TelegramSubscription.is_active == True
        ).all()
        
        if not subscriptions:
            logger.info("Нет активных подписок")
            return
        
        # Группировать подписки по филиалам
        subscriptions_by_branch = {}
        for sub in subscriptions:
            if sub.branch_id not in subscriptions_by_branch:
                subscriptions_by_branch[sub.branch_id] = []
            subscriptions_by_branch[sub.branch_id].append(sub)
        
        # Отправить уведомления
        sent_count = 0
        for review in new_reviews:
            if review.branch_id in subscriptions_by_branch:
                branch_subscriptions = subscriptions_by_branch[review.branch_id]
                
                for subscription in branch_subscriptions:
                    try:
                        # Создать объект для отправки
                        class ChatContext:
                            def __init__(self, chat_id, bot):
                                self.chat_id = chat_id
                                self.bot = bot
                        
                        context = ChatContext(subscription.user_id, application.bot)
                        await send_review_message(context, review, show_branch=True)
                        sent_count += 1
                        
                        # Небольшая задержка для соблюдения лимитов API
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления пользователю {subscription.user_id}: {e}")
            
            # Пометить отзыв как отправленный
            review.sent_to_telegram = True
        
        db.commit()
        logger.info(f"Отправлено {sent_count} уведомлений")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Основная функция"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return
    
    # Создать приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавить обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("reviews", reviews_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Запустить бота
    logger.info("Telegram Bot запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()