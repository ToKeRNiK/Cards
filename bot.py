import os
import json
import random
import logging
import psycopg2
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from psycopg2.extras import RealDictCursor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация - получаем данные из переменных окружения Railway
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8295319122:AAFGvZ1GFqPv8EkCTQnXjSKzd4dOG8rz1bg')
COOLDOWN_MINUTES = 5

# Настройки базы данных
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:GjvKELSoRVzbyXCnxEMBdWvOTiCvufbs@postgres.railway.internal:5432/railway')

# ==================== КОНФИГУРАЦИЯ СОБЫТИЙ ====================
EVENTS_CONFIG = {
    "Казань2025": {
        "name": "Казань2025",
        "key": "Казань",
        "active": False,
        "start_date": "2025-10-27",
        "end_date": "2025-10-29", 
        "emoji": "🏙️",
        "chance": 8
    },
    "Хэллоуин2025": {
        "name": "Хэллоуин2025", 
        "key": "Хэллоуин",
        "active": True,
        "start_date": "2025-10-29",
        "end_date": "2025-10-31",
        "emoji": "🎃",
        "chance": 8
    }
}

# Активное событие
CURRENT_EVENT = "Хэллоуин2025"
EVENT_CONFIG = EVENTS_CONFIG[CURRENT_EVENT]

# ==================== ОСНОВНЫЕ КАРТОЧКИ ====================
RARITY_GROUPS = {
    "Редкая": {
        "base_chance": 30.1,
        "adjusted_chance": 27.692,
        "emoji": "🟢",
        "cards": [
            {"id": 2.1, "name": "Два задрота", "image": "cards/Rare/card2.1.jpg", "points": 50},
            {"id": 2.2, "name": "Умный оператор в очках скачать обои", "image": "cards/Rare/card2.2.jpg", "points": 50},
            {"id": 2.3, "name": "Костя Водолаз", "image": "cards/Rare/card2.3.jpg", "points": 50},
            {"id": 2.4, "name": "Михаил Динозавр", "image": "cards/Rare/card2.4.jpg", "points": 50},
            {"id": 2.5, "name": "Михаил Мевдед", "image": "cards/Rare/card2.5.jpg", "points": 50},
            {"id": 2.6, "name": "Бургер Кинг", "image": "cards/Rare/card2.6.jpg", "points": 50},
            {"id": 2.7, "name": "Служебное помещение", "image": "cards/Rare/card2.7.jpg", "points": 50},
            {"id": 2.8, "name": "Оператор опять нюхает", "image": "cards/Rare/card2.8.jpg", "points": 50},
            {"id": 2.9, "name": "Костя", "image": "cards/Rare/card2.9.jpg", "points": 50},
        ]
    },
    "Сверхредкая": {
        "base_chance": 23.8,
        "adjusted_chance": 21.896,
        "emoji": "🔵",
        "cards": [
            {"id": 3, "name": "Ярик", "image": "cards/SuperRare/card3.jpg", "points": 200},
            {"id": 3.1, "name": "УВЗ", "image": "cards/SuperRare/card3.1.jpg", "points": 200},
            {"id": 3.2, "name": "Чижик", "image": "cards/SuperRare/card3.2.jpg", "points": 200},
            {"id": 3.3, "name": "Фикс в Прайме", "image": "cards/SuperRare/card3.3.jpg", "points": 200},
            {"id": 3.4, "name": "Клубничная кремка", "image": "cards/SuperRare/card3.4.jpg", "points": 200},
            {"id": 3.5, "name": "Оператор у зеркала", "image": "cards/SuperRare/card3.5.jpg", "points": 200},
            {"id": 3.6, "name": "Молочная кремка", "image": "cards/SuperRare/card3.6.jpg", "points": 200},
            {"id": 3.7, "name": "Свинья", "image": "cards/SuperRare/card3.7.jpg", "points": 200},
        ]
    },
    "Эпическая": {
        "base_chance": 17.6,
        "adjusted_chance": 16.192,
        "emoji": "🟣",
        "cards": [
            {"id": 4, "name": "Михаил Динозавр", "image": "cards/Epic/card4.jpg", "points": 1000},
            {"id": 4.1, "name": "Стёпа Автомобилист", "image": "cards/Epic/card4.1.jpg", "points": 1000},
            {"id": 4.2, "name": "Киммих mentality", "image": "cards/Epic/card4.2.jpg", "points": 1000},
            {"id": 4.3, "name": "Весёлый Михаил Медведь", "image": "cards/Epic/card4.3.jpg", "points": 1000},
            {"id": 4.4, "name": "Грустный Тимофей", "image": "cards/Epic/card4.4.jpg", "points": 1000},
            {"id": 4.5, "name": "Вёселый Тимофей", "image": "cards/Epic/card4.5.jpg", "points": 1000},
            {"id": 4.6, "name": "Мирослав и королевские кабаны", "image": "cards/Epic/card4.6.jpg", "points": 1000},
            {"id": 4.7, "name": "Кремка с морской солью", "image": "cards/Epic/card4.7.jpg", "points": 1000},
            {"id": 4.8, "name": "Вкусно и точка", "image": "cards/Epic/card4.8.jpg", "points": 1000},
            {"id": 4.9, "name": "Шапочка для плавания", "image": "cards/Epic/card4.9.jpg", "points": 1000},
        ]
    },
    "Мифическая": {
        "base_chance": 15.6,
        "adjusted_chance": 14.352,
        "emoji": "🔴",
        "cards": [
            {"id": 5, "name": "Сигма Михаил Медведь", "image": "cards/Mythic/card5.jpg", "points": 5000},
            {"id": 5.1, "name": "Гриша Шалун", "image": "cards/Mythic/card5.1.jpg", "points": 5000},
            {"id": 5.2, "name": "ЕВРАЗ", "image": "cards/Mythic/card5.2.jpg", "points": 5000},
            {"id": 5.3, "name": "Счастливый оператор", "image": "cards/Mythic/card5.3.jpg", "points": 5000},
            {"id": 5.4, "name": "Михаил Чикатило", "image": "cards/Mythic/card5.4.jpg", "points": 5000},
            {"id": 5.5, "name": "Миша Combination 2", "image": "cards/Mythic/card5.5.jpg", "points": 5000},
            {"id": 5.6, "name": "Ваня Макака", "image": "cards/Mythic/card5.6.jpg", "points": 5000},
            {"id": 5.7, "name": "Мирослав с автоматом", "image": "cards/Mythic/card5.7.jpg", "points": 5000},
            {"id": 5.8, "name": "Кофейная кремка", "image": "cards/Mythic/card5.8.jpg", "points": 5000},
            {"id": 5.9, "name": "Миша Медведь на ОБЖ", "image": "cards/Mythic/card5.9.jpg", "points": 5000},
        ]
    },
    "Легендарная": {
        "base_chance": 10.4,
        "adjusted_chance": 9.568,
        "emoji": "🟡",
        "cards": [
            {"id": 6, "name": "Стёпа с фанатами", "image": "cards/Legendary/card6.jpg", "points": 10000},
            {"id": 6.1, "name": "Тимофей и Ваня", "image": "cards/Legendary/card6.1.jpg", "points": 10000},
            {"id": 6.2, "name": "Михаил Мевдедь после сорев", "image": "cards/Legendary/card6.2.jpg", "points": 10000},
            {"id": 6.3, "name": "Оператор с цветочком", "image": "cards/Legendary/card6.3.jpg", "points": 10000},
            {"id": 6.4, "name": "Бульба Мен", "image": "cards/Legendary/card6.4.jpg", "points": 10000},
            {"id": 6.5, "name": "Казанский Таракан", "image": "cards/Legendary/card6.5.jpg", "points": 10000},
            {"id": 6.6, "name": "Миша Combination", "image": "cards/Legendary/card6.6.jpg", "points": 10000},
            {"id": 6.7, "name": "Михаил Медвед на соревах", "image": "cards/Legendary/card6.7.jpg", "points": 10000},
            {"id": 6.8, "name": "Марк Хайзенберг", "image": "cards/Legendary/card6.8.jpg", "points": 10000},
            {"id": 6.9, "name": "Сигма и 27", "image": "cards/Legendary/card6.9.jpg", "points": 10000},
            {"id": 6.11, "name": "Рик Граймс", "image": "cards/Legendary/card6.10.jpg", "points": 10000},
            {"id": 6.12, "name": "Рик Граймс", "image": "cards/Legendary/card6.11.jpg", "points": 10000},
        ]
    },
    "Секретная": {
        "base_chance": 2,
        "adjusted_chance": 1.84,
        "emoji": "⚫️",
        "cards": [
            {"id": 7, "name": "Который час?", "image": "cards/Secret/card7.jpg", "points": 20000},
            {"id": 7.1, "name": "Держатель яиц Ярик", "image": "cards/Secret/card7.1.jpg", "points": 20000},
            {"id": 7.2, "name": "Кефас", "image": "cards/Secret/card7.2.jpg", "points": 20000},
            {"id": 7.3, "name": "Владелец Кефаса", "image": "cards/Secret/card7.3.jpg", "points": 20000},
            {"id": 7.4, "name": "Стёпа жуёт шапочку", "image": "cards/Secret/card7.4.jpg", "points": 20000},
            {"id": 7.5, "name": "Владелец Бургер Кинга", "image": "cards/Secret/card7.5.jpg", "points": 20000},
            {"id": 7.6, "name": "Михаил Медведь купил Нигерию", "image": "cards/Secret/card7.6.jpg", "points": 20000},
            {"id": 7.7, "name": "twenty-seven", "image": "cards/Secret/card7.7.jpg", "points": 20000},
            {"id": 7.8, "name": "Марк в розовой машине", "image": "cards/Secret/card7.8.jpg", "points": 20000},
        ]
    },
    "Эксклюзивная": {
        "base_chance": 0.5,
        "adjusted_chance": 0.46,
        "emoji": "🟠",
        "cards": [
            {"id": 8, "name": "Миши в поезде", "image": "cards/Exclusive/card8.jpg", "points": 50000},
            {"id": 8.1, "name": "Миши в Туапсе", "image": "cards/Exclusive/card8.1.jpg", "points": 50000},
            {"id": 8.2, "name": "Место спавна гадостей", "image": "cards/Exclusive/card8.2.jpg", "points": 50000},
            {"id": 8.3, "name": "Президентский", "image": "cards/Exclusive/card8.3.jpg", "points": 50000},
        ]
    },
}

# ==================== КАРТОЧКИ СОБЫТИЙ ====================
EVENT_CARDS = {
    "Казань": {
        "chance": EVENTS_CONFIG["Казань2025"]["chance"],
        "emoji": EVENTS_CONFIG["Казань2025"]["emoji"],
        "cards": [
            {"id": 9.1, "name": "Оператор в Казани", "image": "cards/Kazan/card9.1.jpg", "points": 25000},
            {"id": 9.2, "name": "Оператор в казанском самолёте", "image": "cards/Kazan/card9.2.jpg", "points": 25000},
            {"id": 9.3, "name": "Миша Мевдедь с казанским медведем", "image": "cards/Kazan/card9.3.jpg", "points": 25000},
            {"id": 9.4, "name": "Михаил Динозавр в Казани", "image": "cards/Kazan/card9.4.jpg", "points": 25000},
            {"id": 9.5, "name": "Мини Литвин в Казани", "image": "cards/Kazan/card9.5.jpg", "points": 25000},
            {"id": 9.6, "name": "Легендарная четверка перед Казанью", "image": "cards/Kazan/card9.6.jpg", "points": 25000},
            {"id": 9.7, "name": "'Видишь вон там вон дроны летят'", "image": "cards/Kazan/card9.7.jpg", "points": 25000},
            {"id": 9.8, "name": "Оператор оформил закид", "image": "cards/Kazan/card9.8.jpg", "points": 25000},
        ]
    },
    "Хэллоуин": {
        "chance": EVENTS_CONFIG["Хэллоуин2025"]["chance"],
        "emoji": EVENTS_CONFIG["Хэллоуин2025"]["emoji"],
        "cards": [
            {"id": 10.1, "name": "Хэллоуинский Миша Медведь", "image": "cards/Halloween/card10.1.jpg", "points": 30000},
            {"id": 10.2, "name": "Хэллоуинский Ярик", "image": "cards/Halloween/card10.2.jpg", "points": 30000},
            {"id": 10.3, "name": "Хэллоуинский Миша Динозавр", "image": "cards/Halloween/card10.3.jpg", "points": 30000},
            {"id": 10.4, "name": "Хэллоуинский Оператор", "image": "cards/Halloween/card10.4.jpg", "points": 30000},
            {"id": 10.5, "name": "Хэллоуинский Мини Литвин", "image": "cards/Halloween/card10.5.jpg", "points": 30000},
        ]
    },
}

# ==================== ПРОМОКОДЫ ====================
PROMOCODES = {
    "secret23gifting": {
        "type": "random_rarity",
        "rarity": "Секретная",
        "uses_left": 1,
        "max_uses": 1,
        "description": "Случайная секретная карта"
    },
    "legendary24gifting": {
        "type": "random_rarity", 
        "rarity": "Легендарная",
        "uses_left": 1,
        "max_uses": 1,
        "description": "Случайная легендарная карта"
    },
    "yarikgivt2025": {
        "type": "specific_card",
        "card_id": 7.1,
        "uses_left": 1,
        "max_uses": 1,
        "description": "Держатель яиц Ярик"
    },
    "rickgrimespeakedit2025": {
        "type": "specific_card",
        "card_id": 6.11,
        "uses_left": 2,
        "max_uses": 2,
        "description": "Рик Граймс"
    },
    "kotoriyhour2025": {
        "type": "specific_card",
        "card_id": 7,
        "uses_left": 5,
        "max_uses": 5,
        "description": "Который час?"
    },
    "halakefasiche4327": {
        "type": "specific_card",
        "card_id": 7.2,
        "uses_left": 3,
        "max_uses": 3,
        "description": "Кефас"
    },
    "stem27onixfree": {
        "type": "specific_card", 
        "card_id": 7.7,
        "uses_left": 5,
        "max_uses": 5,
        "description": "twenty-seven"
    },
    "kazanrandom2025": {
        "type": "random_event",
        "event": "Казань",
        "uses_left": 10,
        "max_uses": 10,
        "description": "Случайная карточка из события Казань"
    },
    "halloweenrandom2025": {
        "type": "random_event",
        "event": "Хэллоуин",
        "uses_left": 10,
        "max_uses": 10,
        "description": "Случайная карточка из события Хэллоуин"
    },
}

# ==================== БАЗА ДАННЫХ ====================
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    """Инициализация базы данных"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            inventory JSONB,
            total_points INTEGER DEFAULT 0,
            last_used TIMESTAMP WITH TIME ZONE,
            used_promocodes JSONB
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            rarity TEXT,
            card_id REAL,
            event_name TEXT,
            uses_left INTEGER,
            max_uses INTEGER,
            description TEXT
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS used_promocodes (
            user_id TEXT,
            promo_code TEXT,
            used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (user_id, promo_code)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            trade_id SERIAL PRIMARY KEY,
            user1_id TEXT NOT NULL,
            user2_id TEXT NOT NULL,
            user1_card_id REAL NOT NULL,
            user2_card_id REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        )
    ''')
    
    for code, data in PROMOCODES.items():
        cur.execute('''
            INSERT INTO promocodes (code, type, rarity, card_id, event_name, uses_left, max_uses, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE SET
                uses_left = EXCLUDED.uses_left
        ''', (
            code,
            data["type"],
            data.get("rarity"),
            data.get("card_id"),
            data.get("event"),
            data["uses_left"],
            data["max_uses"],
            data["description"]
        ))
    
    conn.commit()
    cur.close()
    conn.close()

def load_user_data():
    """Загрузка всех пользователей из базы данных"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('SELECT * FROM users')
    users = cur.fetchall()
    
    user_data = {}
    for user in users:
        user_data[user['user_id']] = {
            "inventory": user['inventory'] or [],
            "total_points": user['total_points'] or 0,
            "last_used": user['last_used'].isoformat() if user['last_used'] else None,
            "used_promocodes": user['used_promocodes'] or []
        }
    
    cur.close()
    conn.close()
    return user_data

def save_user_data(data):
    """Сохранение данных пользователя в базу данных"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    for user_id, user_info in data.items():
        cur.execute('''
            INSERT INTO users (user_id, inventory, total_points, last_used, used_promocodes)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                inventory = EXCLUDED.inventory,
                total_points = EXCLUDED.total_points,
                last_used = EXCLUDED.last_used,
                used_promocodes = EXCLUDED.used_promocodes
        ''', (
            user_id,
            json.dumps(user_info["inventory"]),
            user_info["total_points"],
            user_info["last_used"],
            json.dumps(user_info.get("used_promocodes", []))
        ))
    
    conn.commit()
    cur.close()
    conn.close()

def load_promo_data():
    """Загрузка данных промокодов из базы данных"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('SELECT * FROM promocodes')
    promos = cur.fetchall()
    
    promo_data = {}
    for promo in promos:
        promo_data[promo['code']] = {
            "type": promo['type'],
            "rarity": promo['rarity'],
            "card_id": promo['card_id'],
            "event": promo['event_name'],
            "uses_left": promo['uses_left'],
            "max_uses": promo['max_uses'],
            "description": promo['description']
        }
    
    cur.close()
    conn.close()
    return promo_data

def save_promo_data(data):
    """Сохранение данных промокодов в базу данных"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    for code, promo_info in data.items():
        cur.execute('''
            INSERT INTO promocodes (code, type, rarity, card_id, event_name, uses_left, max_uses, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE SET
                uses_left = EXCLUDED.uses_left
        ''', (
            code,
            promo_info["type"],
            promo_info.get("rarity"),
            promo_info.get("card_id"),
            promo_info.get("event"),
            promo_info["uses_left"],
            promo_info["max_uses"],
            promo_info["description"]
        ))
    
    conn.commit()
    cur.close()
    conn.close()

def has_user_used_promo(user_id, promo_code):
    """Проверка, использовал ли пользователь промокод"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT 1 FROM used_promocodes WHERE user_id = %s AND promo_code = %s', (user_id, promo_code))
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    return result is not None

def mark_promo_used(user_id, promo_code):
    """Пометить промокод как использованный пользователем"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO used_promocodes (user_id, promo_code)
        VALUES (%s, %s)
        ON CONFLICT (user_id, promo_code) DO NOTHING
    ''', (user_id, promo_code))
    
    conn.commit()
    cur.close()
    conn.close()

# ==================== СИСТЕМА ТРЕЙДОВ ====================
def create_trade(user1_id, user2_id, user1_card_id, user2_card_id):
    """Создание трейда между игроками"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO trades (user1_id, user2_id, user1_card_id, user2_card_id)
        VALUES (%s, %s, %s, %s)
        RETURNING trade_id
    ''', (user1_id, user2_id, user1_card_id, user2_card_id))
    
    trade_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    return trade_id

def get_trade(trade_id):
    """Получение информации о трейде"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('SELECT * FROM trades WHERE trade_id = %s', (trade_id,))
    trade = cur.fetchone()
    
    cur.close()
    conn.close()
    return trade

def update_trade_status(trade_id, status):
    """Обновление статуса трейда"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if status == 'completed':
        cur.execute('''
            UPDATE trades 
            SET status = %s, completed_at = NOW()
            WHERE trade_id = %s
        ''', (status, trade_id))
    else:
        cur.execute('''
            UPDATE trades 
            SET status = %s
            WHERE trade_id = %s
        ''', (status, trade_id))
    
    conn.commit()
    cur.close()
    conn.close()

def get_user_trades(user_id):
    """Получение всех трейдов пользователя"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('''
        SELECT * FROM trades 
        WHERE (user1_id = %s OR user2_id = %s) 
        AND status = 'pending'
        ORDER BY created_at DESC
    ''', (user_id, user_id))
    
    trades = cur.fetchall()
    cur.close()
    conn.close()
    return trades

def execute_trade(trade_id):
    """Выполнение трейда - обмен карточками"""
    trade = get_trade(trade_id)
    if not trade:
        return False
    
    user1_id = trade['user1_id']
    user2_id = trade['user2_id']
    user1_card_id = trade['user1_card_id']
    user2_card_id = trade['user2_card_id']
    
    user_data = load_user_data()
    
    # Проверяем, что у пользователей еще есть эти карточки
    user1_has_card = any(card['card_id'] == user1_card_id for card in user_data[user1_id]['inventory'])
    user2_has_card = any(card['card_id'] == user2_card_id for card in user_data[user2_id]['inventory'])
    
    if not user1_has_card or not user2_has_card:
        return False
    
    # Находим и удаляем карточки
    user1_card_to_remove = None
    for i, card in enumerate(user_data[user1_id]['inventory']):
        if card['card_id'] == user1_card_id:
            user1_card_to_remove = user_data[user1_id]['inventory'].pop(i)
            user_data[user1_id]['total_points'] -= user1_card_to_remove['points']
            break
    
    user2_card_to_remove = None
    for i, card in enumerate(user_data[user2_id]['inventory']):
        if card['card_id'] == user2_card_id:
            user2_card_to_remove = user_data[user2_id]['inventory'].pop(i)
            user_data[user2_id]['total_points'] -= user2_card_to_remove['points']
            break
    
    if not user1_card_to_remove or not user2_card_to_remove:
        return False
    
    # Добавляем карточки новым владельцам
    user1_card_to_remove['acquired'] = datetime.now(timezone.utc).isoformat()
    user2_card_to_remove['acquired'] = datetime.now(timezone.utc).isoformat()
    
    user_data[user2_id]['inventory'].append(user1_card_to_remove)
    user_data[user2_id]['total_points'] += user1_card_to_remove['points']
    
    user_data[user1_id]['inventory'].append(user2_card_to_remove)
    user_data[user1_id]['total_points'] += user2_card_to_remove['points']
    
    save_user_data(user_data)
    update_trade_status(trade_id, 'completed')
    
    return True

def cancel_trade(trade_id):
    """Отмена трейда"""
    update_trade_status(trade_id, 'cancelled')

# ==================== СИСТЕМА СОБЫТИЙ ====================
def is_event_active():
    """Проверка активности текущего события"""
    if not EVENT_CONFIG["active"]:
        return False
    
    try:
        now = datetime.now(timezone.utc)
        start_date = datetime.fromisoformat(EVENT_CONFIG["start_date"]).replace(tzinfo=timezone.utc)
        end_date = datetime.fromisoformat(EVENT_CONFIG["end_date"]).replace(tzinfo=timezone.utc)
        
        return start_date <= now <= end_date
    except Exception as e:
        logger.error(f"Ошибка проверки события: {e}")
        return False

def get_current_event_key():
    """Получение ключа текущего события"""
    return EVENT_CONFIG["key"]

def get_available_rarities():
    """Получение всех доступных редкостей с учетом активного события"""
    available_rarities = {}
    
    # Основные редкости
    for rarity, data in RARITY_GROUPS.items():
        if is_event_active():
            available_rarities[rarity] = {
                "chance": data["adjusted_chance"],
                "emoji": data["emoji"],
                "cards": data["cards"]
            }
        else:
            available_rarities[rarity] = {
                "chance": data["base_chance"],
                "emoji": data["emoji"],
                "cards": data["cards"]
            }
    
    # Добавляем активное событие
    if is_event_active():
        event_key = get_current_event_key()
        if event_key in EVENT_CARDS:
            available_rarities[event_key] = EVENT_CARDS[event_key]
    
    return available_rarities

def get_random_card():
    """Получение случайной карточки с учетом активного события"""
    available_rarities = get_available_rarities()
    
    # Сначала определяем, выпадет ли событийная карточка
    if is_event_active():
        event_chance = EVENT_CONFIG["chance"]
        if random.random() * 100 < event_chance:
            # Выпадает событийная карточка
            event_key = get_current_event_key()
            if event_key in EVENT_CARDS:
                event_cards = EVENT_CARDS[event_key]["cards"]
                card = random.choice(event_cards)
                card["rarity"] = event_key
                card["emoji"] = EVENT_CARDS[event_key]["emoji"]
                card["rarity_chance"] = EVENT_CARDS[event_key]["chance"]
                return card
    
    # Если событие не активно или не выпала событийная карта, выбираем из основных редкостей
    roll = random.random() * 100
    current = 0
    
    selected_rarity = None
    for rarity, data in available_rarities.items():
        # Пропускаем событийные редкости
        if is_event_active() and rarity == get_current_event_key():
            continue
        current += data["chance"]
        if roll <= current:
            selected_rarity = rarity
            break
    
    if selected_rarity is None:
        available_without_event = {k: v for k, v in available_rarities.items() 
                                 if not (is_event_active() and k == get_current_event_key())}
        selected_rarity = list(available_without_event.keys())[0]
    
    cards_in_rarity = available_rarities[selected_rarity]["cards"]
    card = random.choice(cards_in_rarity)
    
    card["rarity"] = selected_rarity
    card["emoji"] = available_rarities[selected_rarity]["emoji"]
    card["rarity_chance"] = available_rarities[selected_rarity]["chance"]
    
    return card

def get_card_by_id(card_id):
    """Получение карточки по ID"""
    # Сначала ищем в основных карточках
    for rarity_group in RARITY_GROUPS.values():
        for card in rarity_group["cards"]:
            if card["id"] == card_id:
                card["rarity"] = next(r for r, rg in RARITY_GROUPS.items() if card in rg["cards"])
                card["emoji"] = RARITY_GROUPS[card["rarity"]]["emoji"]
                return card
    
    # Затем ищем в карточках события
    for event_key, event_data in EVENT_CARDS.items():
        for card in event_data["cards"]:
            if card["id"] == card_id:
                card["rarity"] = event_key
                card["emoji"] = event_data["emoji"]
                return card
    
    return None

def get_random_card_by_rarity(target_rarity):
    """Получение случайной карточки определенной редкости"""
    available_rarities = get_available_rarities()
    
    if target_rarity not in available_rarities:
        return None
    
    cards_in_rarity = available_rarities[target_rarity]["cards"]
    card = random.choice(cards_in_rarity)
    
    card["rarity"] = target_rarity
    card["emoji"] = available_rarities[target_rarity]["emoji"]
    card["rarity_chance"] = available_rarities[target_rarity]["chance"]
    
    return card

def get_random_event_card(event_name):
    """Получение случайной карточки события"""
    if event_name not in EVENT_CARDS:
        return None
    
    cards_in_event = EVENT_CARDS[event_name]["cards"]
    card = random.choice(cards_in_event)
    
    card["rarity"] = event_name
    card["emoji"] = EVENT_CARDS[event_name]["emoji"]
    card["rarity_chance"] = EVENT_CARDS[event_name]["chance"]
    
    return card

def add_card_to_user(user_id, card):
    """Добавление карточки пользователю"""
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {"inventory": [], "total_points": 0, "last_used": None, "used_promocodes": []}
    
    user_data[user_id]["inventory"].append({
        "card_id": card["id"],
        "name": card["name"],
        "rarity": card["rarity"],
        "points": card["points"],
        "acquired": datetime.now(timezone.utc).isoformat(),
        "from_promo": True
    })
    
    user_data[user_id]["total_points"] += card["points"]
    save_user_data(user_data)
    
    logger.info(f"User {user_id} received card from promo: {card['name']}")

def get_user_card_stats(user_id):
    """Получение статистики по карточкам пользователя"""
    user_data = load_user_data()
    if user_id not in user_data:
        return {}
    
    inventory = user_data[user_id]["inventory"]
    card_stats = {}
    
    for card in inventory:
        card_id = card["card_id"]
        if card_id not in card_stats:
            original_card = get_card_by_id(card_id)
            if original_card:
                card_stats[card_id] = {
                    "name": original_card["name"],
                    "image": original_card["image"],
                    "rarity": original_card["rarity"],
                    "points": original_card["points"],
                    "emoji": original_card["emoji"],
                    "count": 1,
                    "total_points": original_card["points"]
                }
        else:
            card_stats[card_id]["count"] += 1
            card_stats[card_id]["total_points"] += card["points"]
    
    return card_stats

def get_user_duplicate_cards(user_id):
    """Получение дубликатов карточек пользователя"""
    card_stats = get_user_card_stats(user_id)
    duplicates = {card_id: stats for card_id, stats in card_stats.items() if stats["count"] > 1}
    return duplicates

# ==================== КОМАНДЫ БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    available_rarities = get_available_rarities()
    
    rarity_info = "🎲 **Шансы редкостей:**\n"
    for rarity, data in available_rarities.items():
        emoji = data["emoji"]
        chance = data["chance"]
        card_count = len(data["cards"])
        rarity_info += f"{emoji} {rarity}: {chance}% ({card_count} карточек)\n"
    
    event_info = ""
    if is_event_active():
        event_key = get_current_event_key()
        event_cards_count = len(EVENT_CARDS[event_key]["cards"]) if event_key in EVENT_CARDS else 0
        event_info = f"\n🎉 **АКТИВНОЕ СОБЫТИЕ: {EVENT_CONFIG['name']} {EVENT_CONFIG['emoji']}**\n"
        event_info += f"📅 До: {EVENT_CONFIG['end_date']}\n"
        event_info += f"🎴 Специальные карточки: {event_cards_count} шт.\n\n"
    
    await update.message.reply_text(
        f"🎴 **Добро пожаловать в коллекцию карточек!**\n\n"
        f"{event_info}"
        "📖 **Доступные команды:**\n"
        "/getcard - Получить случайную карточку\n"
        "/inventory - Показать вашу коллекцию\n"
        "/rarities - Информация о редкостях\n"
        "/promo <код> - Активировать промокод\n"
        "/event - Информация о событии\n"
        "/trade - Система обмена карточками\n"
        "/mytrades - Мои активные трейды\n\n"
        f"⏰ **Кулдаун:** {COOLDOWN_MINUTES} минут\n\n"
        f"{rarity_info}",
        parse_mode='Markdown'
    )

async def show_event_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_event_active():
        event_key = get_current_event_key()
        event_cards_info = "🎴 **Карточки события:**\n"
        if event_key in EVENT_CARDS:
            for card in EVENT_CARDS[event_key]["cards"]:
                event_cards_info += f"• {card['name']} ({card['points']} очков)\n"
        
        await update.message.reply_text(
            f"🎉 **СОБЫТИЕ: {EVENT_CONFIG['name']} {EVENT_CONFIG['emoji']}**\n\n"
            f"📅 **Период:** {EVENT_CONFIG['start_date']} - {EVENT_CONFIG['end_date']}\n"
            f"🎲 **Шанс выпадения:** {EVENT_CONFIG['chance']}%\n"
            f"⭐ **Особые карточки:** {len(EVENT_CARDS[event_key]['cards'])} шт.\n\n"
            f"{event_cards_info}\n"
            f"⚡ **Успей получить до окончания события!**",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ В данный момент нет активных событий.\n"
            "Следите за обновлениями!",
            parse_mode='Markdown'
        )

async def show_rarities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    available_rarities = get_available_rarities()
    
    rarity_info = "🎲 **Шансы редкостей:**\n"
    for rarity, data in available_rarities.items():
        emoji = data["emoji"]
        chance = data["chance"]
        card_count = len(data["cards"])
        rarity_info += f"{emoji} {rarity}: {chance}% ({card_count} карточек)\n"
    
    if is_event_active():
        rarity_info += f"\n🎉 **Событие {EVENT_CONFIG['name']} активно до {EVENT_CONFIG['end_date']}**"
    
    await update.message.reply_text(rarity_info, parse_mode='Markdown')

async def get_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = load_user_data()

    last_used = user_data.get(user_id, {}).get('last_used')
    if last_used:
        if last_used.endswith('Z'):
            last_time = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
        else:
            last_time = datetime.fromisoformat(last_used)
        
        current_time = datetime.now(timezone.utc)
        
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        
        time_passed = current_time - last_time
        cooldown_duration = timedelta(minutes=COOLDOWN_MINUTES)
        
        if time_passed < cooldown_duration:
            remaining_time = cooldown_duration - time_passed
            total_seconds = int(remaining_time.total_seconds())
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                time_message = f"{hours} часов {minutes} минут {seconds} секунд"
            elif minutes > 0:
                time_message = f"{minutes} минут {seconds} секунд"
            else:
                time_message = f"{seconds} секунд"
                
            await update.message.reply_text(
                f"⏳ Следующая карточка будет доступна через {time_message}"
            )
            return

    card = get_random_card()
    
    # Специальное сообщение для карточек события
    event_notice = ""
    if is_event_active() and card["rarity"] == get_current_event_key():
        event_notice = f"\n🎉 **ЭКСКЛЮЗИВНАЯ КАРТОЧКА СОБЫТИЯ {EVENT_CONFIG['name']}!**"
    
    caption = (
        f"🎴 **Вы получили карточку:** {card['name']}\n"
        f"{card['emoji']} **Редкость:** {card['rarity']}\n"
        f"⭐ **Очки:** {card['points']}\n"
        f"🎲 Шанс редкости: {card['rarity_chance']}%"
        f"{event_notice}"
    )

    try:
        with open(card['image'], 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=caption, parse_mode='Markdown')
    except FileNotFoundError:
        await update.message.reply_text(f"❌ Ошибка: изображение {card['image']} не найдено")

    if user_id not in user_data:
        user_data[user_id] = {"inventory": [], "total_points": 0, "last_used": None, "used_promocodes": []}
    
    user_data[user_id]["inventory"].append({
        "card_id": card["id"],
        "name": card["name"],
        "rarity": card["rarity"],
        "points": card["points"],
        "acquired": datetime.now(timezone.utc).isoformat()
    })
    
    user_data[user_id]["total_points"] += card["points"]
    user_data[user_id]['last_used'] = datetime.now(timezone.utc).isoformat()
    save_user_data(user_data)
    
    logger.info(f"User {user_id} received card: {card['name']} (rarity: {card['rarity']})")

async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data or not user_data[user_id]["inventory"]:
        await update.message.reply_text("📭 Ваша коллекция пуста!\nИспользуйте /getcard чтобы получить первую карточку.")
        return
    
    inventory = user_data[user_id]["inventory"]
    total_points = user_data[user_id]["total_points"]
    
    # Считаем карточки по редкостям
    rarity_count = {}
    for card in inventory:
        rarity = card["rarity"]
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    
    # Создаем клавиатуру с редкостями
    keyboard = []
    
    # Основные редкости
    for rarity in RARITY_GROUPS:
        if rarity in rarity_count and rarity_count[rarity] > 0:
            emoji = RARITY_GROUPS[rarity]["emoji"]
            count = rarity_count[rarity]
            keyboard.append([InlineKeyboardButton(f"{emoji} {rarity} ({count})", callback_data=f"rarity_{rarity}")])
    
    # Карточки событий (все события, которые есть у пользователя)
    for event_config in EVENTS_CONFIG.values():
        event_key = event_config["key"]
        if event_key in rarity_count and rarity_count[event_key] > 0:
            emoji = event_config["emoji"]
            count = rarity_count[event_key]
            # Показываем статус события (активно/завершено)
            event_active = event_config["active"] and is_event_active() and event_config["key"] == get_current_event_key()
            event_status = " 🔚" if not event_active else " 🎉"
            keyboard.append([InlineKeyboardButton(f"{emoji} {event_key} ({count}){event_status}", callback_data=f"rarity_{event_key}")])
    
    # Кнопка для просмотра дубликатов
    duplicates = get_user_duplicate_cards(user_id)
    if duplicates:
        keyboard.append([InlineKeyboardButton("🔄 Дубликаты для обмена", callback_data="show_duplicates")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Информация о событиях
    event_info = ""
    for event_config in EVENTS_CONFIG.values():
        event_key = event_config["key"]
        if event_key in rarity_count:
            event_active = event_config["active"] and is_event_active() and event_config["key"] == get_current_event_key()
            event_status = "завершено" if not event_active else "активно"
            event_info += f"\n{event_config['emoji']} Карточек события {event_key}: {rarity_count[event_key]} шт. ({event_status})"
    
    stats_text = (
        f"📊 **Ваша коллекция:**\n"
        f"📚 Всего карточек: {len(inventory)}\n"
        f"⭐ Всего очков: {total_points}"
        f"{event_info}\n\n"
        f"🎲 **Выберите редкость для просмотра:**"
    )
    
    await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_rarity_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    rarity = query.data.replace("rarity_", "")
    
    card_stats = get_user_card_stats(user_id)
    
    # Фильтруем карточки по выбранной редкости
    rarity_cards = {card_id: stats for card_id, stats in card_stats.items() if stats["rarity"] == rarity}
    
    if not rarity_cards:
        await query.edit_message_text(f"❌ У вас нет карточек редкости: {rarity}")
        return
    
    # Сохраняем данные для навигации
    context.user_data["current_rarity"] = rarity
    context.user_data["rarity_cards"] = list(rarity_cards.items())
    context.user_data["current_card_index"] = 0
    
    await show_card_navigation(query, context)

async def show_card_navigation(query, context):
    user_data = context.user_data
    rarity = user_data["current_rarity"]
    cards = user_data["rarity_cards"]
    current_index = user_data["current_card_index"]
    
    if current_index >= len(cards):
        current_index = 0
        user_data["current_card_index"] = 0
    
    card_id, card_stats = cards[current_index]
    
    # Определяем, является ли карточка событийной
    event_mark = ""
    is_event_card = False
    for event_config in EVENTS_CONFIG.values():
        if card_stats['rarity'] == event_config["key"]:
            is_event_card = True
            event_active = event_config["active"] and is_event_active() and event_config["key"] == get_current_event_key()
            event_mark = " 🎉" if event_active else " ⏳"
            break
    
    caption = (
        f"🎴 **{card_stats['name']}**{event_mark}\n"
        f"{card_stats['emoji']} **Редкость:** {card_stats['rarity']}\n"
        f"📦 **Количество:** {card_stats['count']} шт.\n"
        f"⭐ **Очки за штуку:** {card_stats['points']}\n"
        f"💰 **Всего очков:** {card_stats['total_points']}\n"
        f"🆔 **ID карточки:** {card_id}\n"
        f"📄 **Карточка {current_index + 1} из {len(cards)}**"
    )
    
    # Добавляем информацию о статусе события для событийных карточек
    if is_event_card and not is_event_active():
        caption += f"\n\nℹ️ Событие завершено. Эти карточки больше нельзя получить."
    
    # Создаем клавиатуру навигации
    keyboard = []
    
    nav_buttons = []
    if len(cards) > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="nav_prev"))
        nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{len(cards)}", callback_data="nav_info"))
        nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data="nav_next"))
        keyboard.append(nav_buttons)
    
    # Кнопка для предложения обмена, если есть дубликаты
    if card_stats['count'] > 1:
        keyboard.append([InlineKeyboardButton("🔄 Предложить обмен этой карточкой", callback_data=f"trade_card_{card_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад к редкостям", callback_data="back_to_rarities")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        with open(card_stats['image'], 'rb') as photo:
            if query.message.photo:
                await query.message.edit_media(
                    media=InputMediaPhoto(photo, caption=caption, parse_mode='Markdown'),
                    reply_markup=reply_markup
                )
            else:
                await query.message.reply_photo(
                    photo=photo,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
    except FileNotFoundError:
        if query.message.photo:
            await query.edit_message_text(
                f"❌ Изображение карточки не найдено!\n\n{caption}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.message.reply_text(
                f"❌ Изображение карточки не найдено!\n\n{caption}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    user_data = context.user_data
    
    if "current_card_index" not in user_data or "rarity_cards" not in user_data:
        await query.edit_message_text("❌ Сессия просмотра истекла. Используйте /inventory снова.")
        return
    
    current_index = user_data["current_card_index"]
    total_cards = len(user_data["rarity_cards"])
    
    if action == "nav_prev":
        user_data["current_card_index"] = (current_index - 1) % total_cards
    elif action == "nav_next":
        user_data["current_card_index"] = (current_index + 1) % total_cards
    elif action == "back_to_rarities":
        user_data.pop("current_rarity", None)
        user_data.pop("rarity_cards", None)
        user_data.pop("current_card_index", None)
        await show_inventory_from_callback(query, context)
        return
    elif action == "nav_info":
        pass
    
    await show_card_navigation(query, context)

async def show_inventory_from_callback(query, context):
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data or not user_data[user_id]["inventory"]:
        await query.edit_message_text("📭 Ваша коллекция пуста!\nИспользуйте /getcard чтобы получить первую карточку.")
        return
    
    inventory = user_data[user_id]["inventory"]
    total_points = user_data[user_id]["total_points"]
    
    rarity_count = {}
    for card in inventory:
        rarity = card["rarity"]
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    
    keyboard = []
    
    for rarity in RARITY_GROUPS:
        if rarity in rarity_count and rarity_count[rarity] > 0:
            emoji = RARITY_GROUPS[rarity]["emoji"]
            count = rarity_count[rarity]
            keyboard.append([InlineKeyboardButton(f"{emoji} {rarity} ({count})", callback_data=f"rarity_{rarity}")])
    
    for event_config in EVENTS_CONFIG.values():
        event_key = event_config["key"]
        if event_key in rarity_count and rarity_count[event_key] > 0:
            emoji = event_config["emoji"]
            count = rarity_count[event_key]
            event_active = event_config["active"] and is_event_active() and event_config["key"] == get_current_event_key()
            event_status = " 🔚" if not event_active else " 🎉"
            keyboard.append([InlineKeyboardButton(f"{emoji} {event_key} ({count}){event_status}", callback_data=f"rarity_{event_key}")])
    
    # Кнопка для просмотра дубликатов
    duplicates = get_user_duplicate_cards(user_id)
    if duplicates:
        keyboard.append([InlineKeyboardButton("🔄 Дубликаты для обмена", callback_data="show_duplicates")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    event_info = ""
    for event_config in EVENTS_CONFIG.values():
        event_key = event_config["key"]
        if event_key in rarity_count:
            event_active = event_config["active"] and is_event_active() and event_config["key"] == get_current_event_key()
            event_status = "завершено" if not event_active else "активно"
            event_info += f"\n{event_config['emoji']} Карточек события {event_key}: {rarity_count[event_key]} шт. ({event_status})"
    
    stats_text = (
        f"📊 **Ваша коллекция:**\n"
        f"📚 Всего карточек: {len(inventory)}\n"
        f"⭐ Всего очков: {total_points}"
        f"{event_info}\n\n"
        f"🎲 **Выберите редкость для просмотра:**"
    )
    
    if query.message.photo:
        await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_duplicates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    duplicates = get_user_duplicate_cards(user_id)
    
    if not duplicates:
        await query.edit_message_text("❌ У вас нет дубликатов карточек для обмена.")
        return
    
    keyboard = []
    for card_id, card_stats in duplicates.items():
        button_text = f"{card_stats['emoji']} {card_stats['name']} ({card_stats['count']} шт.)"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"trade_card_{card_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад к коллекции", callback_data="back_to_rarities")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔄 **Ваши дубликаты для обмена:**\n\n"
        "Выберите карточку, которую хотите предложить для обмена:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def start_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    card_id = float(query.data.replace("trade_card_", ""))
    
    # Сохраняем выбранную карточку для трейда
    context.user_data["trade_card_id"] = card_id
    context.user_data["trade_step"] = "get_username"
    
    card = get_card_by_id(card_id)
    if card:
        await query.edit_message_text(
            f"🔄 **Начало обмена**\n\n"
            f"Вы предлагаете: **{card['name']}**\n"
            f"Редкость: {card['emoji']} {card['rarity']}\n\n"
            f"Теперь укажите @username игрока, с которым хотите обменяться:",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text("❌ Ошибка: карточка не найдена.")

async def handle_trade_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if "trade_step" not in context.user_data or context.user_data["trade_step"] != "get_username":
        await update.message.reply_text("❌ Начните обмен заново с помощью /trade")
        return
    
    username = update.message.text.strip()
    if not username.startswith('@'):
        await update.message.reply_text("❌ Укажите @username игрока (начинается с @)")
        return
    
    context.user_data["trade_username"] = username
    context.user_data["trade_step"] = "get_target_card"
    
    await update.message.reply_text(
        f"📝 Теперь укажите ID карточки, которую хотите получить от {username}:\n\n"
        f"Игрок должен использовать команду /inventory чтобы посмотреть ID своих карточек."
    )

async def handle_trade_target_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if "trade_step" not in context.user_data or context.user_data["trade_step"] != "get_target_card":
        await update.message.reply_text("❌ Начните обмен заново с помощью /trade")
        return
    
    try:
        target_card_id = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Укажите корректный ID карточки (число)")
        return
    
    # Проверяем существование карточки
    target_card = get_card_by_id(target_card_id)
    if not target_card:
        await update.message.reply_text("❌ Карточка с таким ID не существует")
        return
    
    context.user_data["trade_target_card_id"] = target_card_id
    
    # Создаем трейд
    user_card_id = context.user_data["trade_card_id"]
    username = context.user_data["trade_username"]
    
    # Здесь должна быть логика поиска user_id по username
    # В реальной реализации нужно хранить username в базе данных
    # Для демонстрации будем использовать фиктивный user_id
    target_user_id = username  # В реальности нужно получить user_id из базы по username
    
    trade_id = create_trade(user_id, target_user_id, user_card_id, target_card_id)
    
    # Очищаем данные трейда
    context.user_data.pop("trade_step", None)
    context.user_data.pop("trade_card_id", None)
    context.user_data.pop("trade_username", None)
    context.user_data.pop("trade_target_card_id", None)
    
    user_card = get_card_by_id(user_card_id)
    
    await update.message.reply_text(
        f"✅ **Предложение обмена создано!**\n\n"
        f"🔄 **Детали обмена:**\n"
        f"• Вы отдаете: {user_card['name']} ({user_card['emoji']} {user_card['rarity']})\n"
        f"• Вы получаете: {target_card['name']} ({target_card['emoji']} {target_card['rarity']})\n"
        f"• Игрок: {username}\n\n"
        f"📋 ID трейда: `{trade_id}`\n\n"
        f"Игрок должен принять обмен с помощью:\n"
        f"`/accepttrade {trade_id}`",
        parse_mode='Markdown'
    )

async def show_my_trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    trades = get_user_trades(user_id)
    
    if not trades:
        await update.message.reply_text("📭 У вас нет активных предложений обмена.")
        return
    
    trade_list = "📋 **Ваши активные трейды:**\n\n"
    
    for trade in trades:
        user1_card = get_card_by_id(trade['user1_card_id'])
        user2_card = get_card_by_id(trade['user2_card_id'])
        
        if user1_card and user2_card:
            trade_list += (
                f"🆔 **ID трейда:** `{trade['trade_id']}`\n"
                f"👤 **Участники:** {trade['user1_id']} ↔️ {trade['user2_id']}\n"
                f"🎴 **Обмен:** {user1_card['name']} ↔️ {user2_card['name']}\n"
                f"📅 **Создан:** {trade['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
            )
            
            if trade['user1_id'] == user_id:
                trade_list += "➡️ Вы инициатор обмена\n"
            else:
                trade_list += "➡️ Вы можете принять этот обмен\n"
            
            trade_list += "---\n\n"
    
    trade_list += "\n💡 **Команды:**\n• `/accepttrade <ID>` - принять обмен\n• `/canceltrade <ID>` - отменить обмен"
    
    await update.message.reply_text(trade_list, parse_mode='Markdown')

async def accept_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID трейда: `/accepttrade <ID>`", parse_mode='Markdown')
        return
    
    try:
        trade_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Укажите корректный ID трейда (число)")
        return
    
    trade = get_trade(trade_id)
    if not trade:
        await update.message.reply_text("❌ Трейд не найден")
        return
    
    if trade['status'] != 'pending':
        await update.message.reply_text("❌ Этот трейд уже обработан")
        return
    
    if trade['user2_id'] != user_id:
        await update.message.reply_text("❌ Вы не можете принять этот трейд")
        return
    
    # Проверяем, что у пользователей еще есть карточки для обмена
    user_data = load_user_data()
    user1_has_card = any(card['card_id'] == trade['user1_card_id'] for card in user_data[trade['user1_id']]['inventory'])
    user2_has_card = any(card['card_id'] == trade['user2_card_id'] for card in user_data[trade['user2_id']]['inventory'])
    
    if not user1_has_card or not user2_has_card:
        await update.message.reply_text("❌ Один из участников больше не имеет карточки для обмена")
        cancel_trade(trade_id)
        return
    
    # Выполняем обмен
    if execute_trade(trade_id):
        user1_card = get_card_by_id(trade['user1_card_id'])
        user2_card = get_card_by_id(trade['user2_card_id'])
        
        await update.message.reply_text(
            f"✅ **Обмен завершен успешно!**\n\n"
            f"🔄 **Вы получили:** {user1_card['name']} ({user1_card['emoji']} {user1_card['rarity']})\n"
            f"🎴 **Вы отдали:** {user2_card['name']} ({user2_card['emoji']} {user2_card['rarity']})",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Ошибка при выполнении обмена")

async def cancel_trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID трейда: `/canceltrade <ID>`", parse_mode='Markdown')
        return
    
    try:
        trade_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Укажите корректный ID трейда (число)")
        return
    
    trade = get_trade(trade_id)
    if not trade:
        await update.message.reply_text("❌ Трейд не найден")
        return
    
    if trade['status'] != 'pending':
        await update.message.reply_text("❌ Этот трейд уже обработан")
        return
    
    if trade['user1_id'] != user_id:
        await update.message.reply_text("❌ Вы можете отменять только свои трейды")
        return
    
    cancel_trade(trade_id)
    await update.message.reply_text("✅ Трейд отменен")

async def trade_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔄 **Система обмена карточками**\n\n"
        "📖 **Как это работает:**\n"
        "1. Используйте /inventory чтобы посмотреть свои карточки\n"
        "2. Нажмите на карточку с дубликатами (количество > 1)\n"
        "3. Нажмите 'Предложить обмен этой карточкой'\n"
        "4. Укажите @username игрока и ID карточки, которую хотите получить\n\n"
        "📋 **Команды:**\n"
        "/trade - начать обмен (альтернативный способ)\n"
        "/mytrades - мои активные трейды\n"
        "/accepttrade <ID> - принять предложенный обмен\n"
        "/canceltrade <ID> - отменить свой трейд\n\n"
        "💡 **Советы:**\n"
        "• Обмениваться можно только дубликатами карточек\n"
        "• Для просмотра ID карточек используйте /inventory\n"
        "• Трейды должны быть взаимно согласованы",
        parse_mode='Markdown'
    )

async def use_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text(
            "🎟️ **Использование промокода:**\n"
            "Введите /promo <код>\n\n"
            "Пример: /promo secret23gifting"
        )
        return
    
    promo_code = context.args[0].lower()
    promo_data = load_promo_data()
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {"inventory": [], "total_points": 0, "last_used": None, "used_promocodes": []}
    
    if "used_promocodes" not in user_data[user_id]:
        user_data[user_id]["used_promocodes"] = []
    
    if has_user_used_promo(user_id, promo_code):
        await update.message.reply_text("❌ Вы уже использовали этот промокод!")
        return
    
    if promo_code not in promo_data:
        await update.message.reply_text("❌ Неверный промокод!")
        return
    
    promo = promo_data[promo_code]
    
    if promo["uses_left"] <= 0:
        await update.message.reply_text("❌ Промокод больше не действителен!")
        return
    
    if promo["type"] == "random_rarity":
        card = get_random_card_by_rarity(promo["rarity"])
        if not card:
            await update.message.reply_text("❌ Ошибка при получении карты!")
            return
    elif promo["type"] == "specific_card":
        card = get_card_by_id(promo["card_id"])
        if not card:
            await update.message.reply_text("❌ Ошибка при получении карты!")
            return
    elif promo["type"] == "random_event":
        card = get_random_event_card(promo["event"])
        if not card:
            await update.message.reply_text("❌ Ошибка при получении карты события!")
            return
    else:
        await update.message.reply_text("❌ Неизвестный тип промокода!")
        return
    
    event_notice = ""
    if promo["type"] == "random_event":
        event_notice = f"\n🎉 **ЭКСКЛЮЗИВНАЯ КАРТОЧКА СОБЫТИЯ {promo['event']}!**"
    
    caption = (
        f"🎁 **Вы активировали промокод!**\n"
        f"🎴 **Получена карточка:** {card['name']}\n"
        f"{card['emoji']} **Редкость:** {card['rarity']}\n"
        f"⭐ **Очки:** {card['points']}\n"
        f"🎟️ Промокод: {promo_code}"
        f"{event_notice}"
    )
    
    try:
        with open(card['image'], 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=caption, parse_mode='Markdown')
    except FileNotFoundError:
        await update.message.reply_text(f"❌ Ошибка: изображение {card['image']} не найдено")
        return
    
    promo_data[promo_code]["uses_left"] -= 1
    save_promo_data(promo_data)
    
    mark_promo_used(user_id, promo_code)
    
    add_card_to_user(user_id, card)
    
    uses_left = promo_data[promo_code]["uses_left"]
    if uses_left > 0:
        uses_info = f"Осталось использований: {uses_left}/{promo['max_uses']}"
    else:
        uses_info = "Промокод полностью использован!"
    
    await update.message.reply_text(f"✅ Промокод успешно активирован!\n{uses_info}")

if __name__ == "__main__":
    init_db()
    
    # Проверка существования карточек
    for rarity, data in RARITY_GROUPS.items():
        for card in data["cards"]:
            if not os.path.exists(card['image']):
                logger.warning(f"Image not found: {card['image']}")
    
    for event_key, event_data in EVENT_CARDS.items():
        for card in event_data["cards"]:
            if not os.path.exists(card['image']):
                logger.warning(f"Event image not found: {card['image']}")
    
    total_base_chance = sum(data["base_chance"] for data in RARITY_GROUPS.values())
    if abs(total_base_chance - 100.0) > 0.1:
        logger.warning(f"Total base chance is {total_base_chance}% (should be 100%)")
    else:
        logger.info(f"Total base chance: {total_base_chance}% (correct)")

    if is_event_active():
        logger.info(f"Событие '{EVENT_CONFIG['name']}' активно!")
    else:
        logger.info("Событие не активно")

    load_promo_data()

    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getcard", get_card))
    application.add_handler(CommandHandler("inventory", show_inventory))
    application.add_handler(CommandHandler("rarities", show_rarities))
    application.add_handler(CommandHandler("promo", use_promo))
    application.add_handler(CommandHandler("event", show_event_info))
    application.add_handler(CommandHandler("trade", trade_help))
    application.add_handler(CommandHandler("mytrades", show_my_trades))
    application.add_handler(CommandHandler("accepttrade", accept_trade))
    application.add_handler(CommandHandler("canceltrade", cancel_trade_command))
    
    # Обработчики для текстовых сообщений (для трейдов)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trade_username))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trade_target_card))
    
    application.add_handler(CallbackQueryHandler(show_rarity_cards, pattern="^rarity_"))
    application.add_handler(CallbackQueryHandler(handle_navigation, pattern="^nav_"))
    application.add_handler(CallbackQueryHandler(show_inventory_from_callback, pattern="^back_to_rarities$"))
    application.add_handler(CallbackQueryHandler(show_duplicates, pattern="^show_duplicates$"))
    application.add_handler(CallbackQueryHandler(start_trade, pattern="^trade_card_"))
    
    logger.info("Бот запущен на Railway...")
    application.run_polling()
