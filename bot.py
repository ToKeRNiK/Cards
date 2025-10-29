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
        "end_date": "2025-10-29",
        "emoji": "🎃",
        "chance": 8
    }
}

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

# ==================== КРАФТИНГ ====================
CRAFT_RECIPES = {
    "Редкая": {
        "ingredients": [{"rarity": "Редкая", "count": 5}],
        "result": "Сверхредкая",
        "chance": 100,
        "description": "5 редких → 1 сверхредкая"
    },
    "Сверхредкая": {
        "ingredients": [{"rarity": "Сверхредкая", "count": 3}],
        "result": "Эпическая", 
        "chance": 100,
        "description": "3 сверхредких → 1 эпическая"
    },
    "Эпическая": {
        "ingredients": [{"rarity": "Эпическая", "count": 3}],
        "result": "Мифическая",
        "chance": 80,
        "description": "3 эпических → 1 мифическая (80% шанс)"
    },
    "Мифическая": {
        "ingredients": [{"rarity": "Мифическая", "count": 2}],
        "result": "Легендарная",
        "chance": 60,
        "description": "2 мифических → 1 легендарная (60% шанс)"
    },
    "Легендарная": {
        "ingredients": [{"rarity": "Легендарная", "count": 2}],
        "result": "Секретная",
        "chance": 40,
        "description": "2 легендарных → 1 секретная (40% шанс)"
    },
    "Секретная": {
        "ingredients": [{"rarity": "Секретная", "count": 2}],
        "result": "Эксклюзивная",
        "chance": 20,
        "description": "2 секретных → 1 эксклюзивная (20% шанс)"
    }
}

# ==================== ЕЖЕДНЕВНЫЕ НАГРАДЫ ====================
DAILY_REWARDS = {
    1: {"type": "points", "amount": 1000, "description": "1000 очков"},
    2: {"type": "random_card", "rarity": "Редкая", "description": "Случайная редкая карта"},
    3: {"type": "points", "amount": 2000, "description": "2000 очков"},
    4: {"type": "random_card", "rarity": "Сверхредкая", "description": "Случайная сверхредкая карта"},
    5: {"type": "points", "amount": 5000, "description": "5000 очков"},
    6: {"type": "random_card", "rarity": "Эпическая", "description": "Случайная эпическая карта"},
    7: {"type": "special", "description": "СУПЕР ПРИЗ: случайная легендарная карта!"}
}

# ==================== КАСТОМНЫЕ ПРОФИЛИ ====================
PROFILE_TITLES = {
    "Новичок": {"requirement": "default", "emoji": "👶"},
    "Коллекционер": {"requirement": "total_cards_50", "emoji": "📚"},
    "Эксперт": {"requirement": "total_cards_100", "emoji": "🎓"},
    "Мастер": {"requirement": "total_cards_200", "emoji": "🏆"},
    "Легенда": {"requirement": "total_cards_500", "emoji": "⭐"},
    "Охотник за редкостями": {"requirement": "all_rare_cards", "emoji": "🎯"},
    "Богач": {"requirement": "total_points_100000", "emoji": "💰"},
    "Искатель приключений": {"requirement": "all_event_cards", "emoji": "🧭"}
}

PROFILE_FRAMES = {
    "Стандартная": {"requirement": "default", "color": "⚪"},
    "Золотая": {"requirement": "total_points_50000", "color": "🟡"},
    "Платиновая": {"requirement": "total_points_200000", "color": "⚪"},
    "Радужная": {"requirement": "all_rarity_cards", "color": "🌈"},
    "Огненная": {"requirement": "total_cards_300", "color": "🔥"},
    "Ледяная": {"requirement": "special_achievement", "color": "❄️"}
}

# ==================== МИНИ-ИГРЫ ====================
MINIGAME_CONFIG = {
    "roulette": {
        "win_chance": 40,
        "multipliers": {
            "Редкая": 2,
            "Сверхредкая": 3,
            "Эпическая": 5,
            "Мифическая": 8,
            "Легендарная": 15,
            "Секретная": 25,
            "Эксклюзивная": 50
        }
    },
    "guess_rarity": {
        "reward_multiplier": 2,
        "time_limit": 30
    }
}

# ==================== БАЗА ДАННЫХ ====================
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    """Инициализация базы данных"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            inventory JSONB,
            total_points INTEGER DEFAULT 0,
            last_used TIMESTAMP WITH TIME ZONE,
            used_promocodes JSONB,
            daily_streak INTEGER DEFAULT 0,
            last_daily TIMESTAMP WITH TIME ZONE,
            profile_data JSONB
        )
    ''')
    
    # Таблица промокодов
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
    
    # Таблица использованных промокодов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS used_promocodes (
            user_id TEXT,
            promo_code TEXT,
            used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (user_id, promo_code)
        )
    ''')
    
    # Таблица обменов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            trade_id SERIAL PRIMARY KEY,
            user1_id TEXT NOT NULL,
            user2_id TEXT NOT NULL,
            user1_cards JSONB,
            user2_cards JSONB,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        )
    ''')
    
    # Инициализация промокодов
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
            "used_promocodes": user['used_promocodes'] or [],
            "daily_streak": user['daily_streak'] or 0,
            "last_daily": user['last_daily'].isoformat() if user['last_daily'] else None,
            "profile_data": user['profile_data'] or {"title": "Новичок", "frame": "Стандартная", "bio": ""}
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
            INSERT INTO users (user_id, inventory, total_points, last_used, used_promocodes, daily_streak, last_daily, profile_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                inventory = EXCLUDED.inventory,
                total_points = EXCLUDED.total_points,
                last_used = EXCLUDED.last_used,
                used_promocodes = EXCLUDED.used_promocodes,
                daily_streak = EXCLUDED.daily_streak,
                last_daily = EXCLUDED.last_daily,
                profile_data = EXCLUDED.profile_data
        ''', (
            user_id,
            json.dumps(user_info["inventory"]),
            user_info["total_points"],
            user_info["last_used"],
            json.dumps(user_info.get("used_promocodes", [])),
            user_info.get("daily_streak", 0),
            user_info.get("last_daily"),
            json.dumps(user_info.get("profile_data", {"title": "Новичок", "frame": "Стандартная", "bio": ""}))
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

# ==================== ОБМЕН КАРТОЧКАМИ ====================
def create_trade(user1_id, user2_id, user1_cards, user2_cards):
    """Создание обмена"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO trades (user1_id, user2_id, user1_cards, user2_cards)
        VALUES (%s, %s, %s, %s)
        RETURNING trade_id
    ''', (user1_id, user2_id, json.dumps(user1_cards), json.dumps(user2_cards)))
    
    trade_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    return trade_id

def get_trade(trade_id):
    """Получение информации об обмене"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('SELECT * FROM trades WHERE trade_id = %s', (trade_id,))
    trade = cur.fetchone()
    
    cur.close()
    conn.close()
    return trade

def update_trade_status(trade_id, status):
    """Обновление статуса обмена"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        UPDATE trades 
        SET status = %s, completed_at = NOW()
        WHERE trade_id = %s
    ''', (status, trade_id))
    
    conn.commit()
    cur.close()
    conn.close()

def get_user_trades(user_id):
    """Получение всех обменов пользователя"""
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
        user_data[user_id] = {
            "inventory": [], 
            "total_points": 0, 
            "last_used": None, 
            "used_promocodes": [],
            "daily_streak": 0,
            "last_daily": None,
            "profile_data": {"title": "Новичок", "frame": "Стандартная", "bio": ""}
        }
    
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

# ==================== КРАФТИНГ ====================
async def show_craft_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню крафта"""
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data or not user_data[user_id]["inventory"]:
        await update.message.reply_text("📭 Ваша коллекция пуста! Сначала получите карточки.")
        return
    
    # Создаем клавиатуру с рецептами крафта
    keyboard = []
    for recipe_name, recipe in CRAFT_RECIPES.items():
        # Проверяем, есть ли у пользователя достаточно карт для крафта
        can_craft = True
        for ingredient in recipe["ingredients"]:
            user_cards = [card for card in user_data[user_id]["inventory"] if card["rarity"] == ingredient["rarity"]]
            if len(user_cards) < ingredient["count"]:
                can_craft = False
                break
        
        button_text = f"{recipe['description']}"
        if not can_craft:
            button_text += " ❌"
        else:
            button_text += " ✅"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"craft_{recipe_name}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="craft_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠️ **Мастерская крафта**\n\n"
        "Выберите рецепт для создания карточек более высокой редкости:\n"
        "✅ - можно скрафтить\n"
        "❌ - недостаточно карт\n\n"
        "Шансы успеха указаны в описании.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_craft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора рецепта крафта"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    action = query.data
    
    if action == "craft_back":
        await query.edit_message_text("🔙 Возврат в главное меню")
        return
    
    if action.startswith("craft_"):
        recipe_name = action.replace("craft_", "")
        await process_craft(query, context, user_id, recipe_name)

async def process_craft(query, context, user_id, recipe_name):
    """Обработка процесса крафта"""
    user_data = load_user_data()
    
    if recipe_name not in CRAFT_RECIPES:
        await query.edit_message_text("❌ Рецепт не найден!")
        return
    
    recipe = CRAFT_RECIPES[recipe_name]
    
    # Проверяем, есть ли достаточно карт
    cards_to_remove = []
    for ingredient in recipe["ingredients"]:
        user_cards = [card for card in user_data[user_id]["inventory"] if card["rarity"] == ingredient["rarity"]]
        if len(user_cards) < ingredient["count"]:
            await query.edit_message_text(f"❌ Недостаточно карт редкости {ingredient['rarity']} для крафта!")
            return
        
        # Выбираем карты для удаления (самые старые)
        cards_to_remove.extend(user_cards[:ingredient["count"]])
    
    # Проверяем шанс успеха
    success = random.random() * 100 <= recipe["chance"]
    
    if success:
        # Успешный крафт - удаляем старые карты и добавляем новую
        for card in cards_to_remove:
            user_data[user_id]["inventory"].remove(card)
            user_data[user_id]["total_points"] -= card["points"]
        
        # Создаем новую карту
        result_card = get_random_card_by_rarity(recipe["result"])
        if result_card:
            user_data[user_id]["inventory"].append({
                "card_id": result_card["id"],
                "name": result_card["name"],
                "rarity": result_card["rarity"],
                "points": result_card["points"],
                "acquired": datetime.now(timezone.utc).isoformat(),
                "from_craft": True
            })
            user_data[user_id]["total_points"] += result_card["points"]
            
            save_user_data(user_data)
            
            # Показываем результат
            caption = (
                f"🎉 **Крафт успешен!**\n\n"
                f"🛠️ Вы скрафтили: {result_card['name']}\n"
                f"{result_card['emoji']} **Редкость:** {result_card['rarity']}\n"
                f"⭐ **Очки:** {result_card['points']}\n"
                f"🎲 **Шанс успеха:** {recipe['chance']}%\n\n"
                f"Использовано карт: {len(cards_to_remove)}"
            )
            
            try:
                with open(result_card['image'], 'rb') as photo:
                    await query.message.reply_photo(photo=photo, caption=caption, parse_mode='Markdown')
            except FileNotFoundError:
                await query.message.reply_text(f"❌ Ошибка: изображение не найдено\n\n{caption}", parse_mode='Markdown')
            
            await query.edit_message_text("🛠️ Крафт завершен!")
        else:
            await query.edit_message_text("❌ Ошибка при создании карты!")
    else:
        # Неудачный крафт - удаляем карты без награды
        for card in cards_to_remove:
            user_data[user_id]["inventory"].remove(card)
            user_data[user_id]["total_points"] -= card["points"]
        
        save_user_data(user_data)
        
        await query.edit_message_text(
            f"💥 **Крафт не удался!**\n\n"
            f"К сожалению, карты были потеряны.\n"
            f"Шанс успеха был: {recipe['chance']}%\n\n"
            f"Попробуйте еще раз!",
            parse_mode='Markdown'
        )

# ==================== ЕЖЕДНЕВНЫЕ НАГРАДЫ ====================
async def daily_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдача ежедневной награды"""
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {
            "inventory": [], 
            "total_points": 0, 
            "last_used": None, 
            "used_promocodes": [],
            "daily_streak": 0,
            "last_daily": None,
            "profile_data": {"title": "Новичок", "frame": "Стандартная", "bio": ""}
        }
    
    now = datetime.now(timezone.utc)
    last_daily = user_data[user_id].get("last_daily")
    
    # Проверяем, можно ли забрать награду
    if last_daily:
        last_daily_date = datetime.fromisoformat(last_daily.replace('Z', '+00:00'))
        if last_daily_date.tzinfo is None:
            last_daily_date = last_daily_date.replace(tzinfo=timezone.utc)
        
        # Проверяем, прошел ли уже день
        time_since_last_daily = now - last_daily_date
        if time_since_last_daily < timedelta(hours=20):
            next_daily = last_daily_date + timedelta(hours=20)
            time_left = next_daily - now
            
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            
            await update.message.reply_text(
                f"⏳ Следующая ежедневная награда будет доступна через {hours}ч {minutes}м\n"
                f"Текущая серия: {user_data[user_id].get('daily_streak', 0)} дней"
            )
            return
        
        # Проверяем, не прервана ли серия
        if time_since_last_daily > timedelta(hours=44):  # 24 + 20 часов
            user_data[user_id]["daily_streak"] = 0
    
    # Увеличиваем серию
    user_data[user_id]["daily_streak"] = user_data[user_id].get("daily_streak", 0) + 1
    streak = user_data[user_id]["daily_streak"]
    
    # Определяем день награды (цикл 7 дней)
    day = ((streak - 1) % 7) + 1
    reward_info = DAILY_REWARDS[day]
    
    # Выдаем награду
    reward_text = f"🎁 **Ежедневная награда - День {day}**\n\n"
    reward_text += f"📅 Серия: {streak} дней\n\n"
    
    if reward_info["type"] == "points":
        points = reward_info["amount"]
        user_data[user_id]["total_points"] += points
        reward_text += f"💰 Вы получили: {points} очков!\n"
        reward_text += f"📝 {reward_info['description']}"
    
    elif reward_info["type"] == "random_card":
        rarity = reward_info["rarity"]
        card = get_random_card_by_rarity(rarity)
        if card:
            user_data[user_id]["inventory"].append({
                "card_id": card["id"],
                "name": card["name"],
                "rarity": card["rarity"],
                "points": card["points"],
                "acquired": datetime.now(timezone.utc).isoformat(),
                "from_daily": True
            })
            user_data[user_id]["total_points"] += card["points"]
            
            reward_text += f"🎴 Вы получили: {card['name']}\n"
            reward_text += f"{card['emoji']} Редкость: {card['rarity']}\n"
            reward_text += f"⭐ Очки: {card['points']}\n"
            reward_text += f"📝 {reward_info['description']}"
            
            # Показываем картинку карты
            try:
                with open(card['image'], 'rb') as photo:
                    await update.message.reply_photo(photo=photo, caption=reward_text, parse_mode='Markdown')
            except FileNotFoundError:
                await update.message.reply_text(f"❌ Ошибка: изображение не найдено\n\n{reward_text}", parse_mode='Markdown')
        else:
            reward_text += "❌ Ошибка при получении карты!"
            await update.message.reply_text(reward_text, parse_mode='Markdown')
    
    elif reward_info["type"] == "special":
        # СУПЕР ПРИЗ - случайная легендарная карта
        card = get_random_card_by_rarity("Легендарная")
        if card:
            user_data[user_id]["inventory"].append({
                "card_id": card["id"],
                "name": card["name"],
                "rarity": card["rarity"],
                "points": card["points"],
                "acquired": datetime.now(timezone.utc).isoformat(),
                "from_daily": True
            })
            user_data[user_id]["total_points"] += card["points"]
            
            reward_text += f"🎉 **СУПЕР ПРИЗ!** 🎉\n\n"
            reward_text += f"🎴 Вы получили: {card['name']}\n"
            reward_text += f"{card['emoji']} Редкость: {card['rarity']}\n"
            reward_text += f"⭐ Очки: {card['points']}\n"
            reward_text += f"📝 {reward_info['description']}"
            
            try:
                with open(card['image'], 'rb') as photo:
                    await update.message.reply_photo(photo=photo, caption=reward_text, parse_mode='Markdown')
            except FileNotFoundError:
                await update.message.reply_text(f"❌ Ошибка: изображение не найдено\n\n{reward_text}", parse_mode='Markdown')
        else:
            reward_text += "❌ Ошибка при получении карты!"
            await update.message.reply_text(reward_text, parse_mode='Markdown')
    
    # Обновляем время последней награды
    user_data[user_id]["last_daily"] = now.isoformat()
    save_user_data(user_data)
    
    if reward_info["type"] != "random_card" and reward_info["type"] != "special":
        await update.message.reply_text(reward_text, parse_mode='Markdown')

# ==================== ОБМЕН КАРТОЧКАМИ ====================
async def start_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать обмен карточками"""
    user_id = str(update.effective_user.id)
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "🤝 **Обмен карточками**\n\n"
            "Использование:\n"
            "/trade @username card_id1,card_id2...\n\n"
            "Пример:\n"
            "/trade @username 2.1,2.2,2.3\n\n"
            "Чтобы посмотреть ID карт, используйте /inventory"
        )
        return
    
    target_username = context.args[0].replace('@', '')
    card_ids = context.args[1].split(',')
    
    # Получаем данные пользователей
    user_data = load_user_data()
    
    # Находим ID целевого пользователя по username
    target_user_id = None
    for uid, data in user_data.items():
        # В реальном боте нужно получать username из Telegram API
        # Здесь используем простую проверку
        if target_username.lower() in uid.lower():
            target_user_id = uid
            break
    
    if not target_user_id:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    
    if target_user_id == user_id:
        await update.message.reply_text("❌ Нельзя обмениваться с самим собой!")
        return
    
    # Проверяем карты пользователя
    user_cards = []
    for card_id_str in card_ids:
        try:
            card_id = float(card_id_str)
            # Проверяем, есть ли такая карта у пользователя
            user_card = next((card for card in user_data[user_id]["inventory"] if card["card_id"] == card_id), None)
            if user_card:
                user_cards.append(user_card)
            else:
                await update.message.reply_text(f"❌ У вас нет карты с ID {card_id}!")
                return
        except ValueError:
            await update.message.reply_text(f"❌ Неверный ID карты: {card_id_str}")
            return
    
    if not user_cards:
        await update.message.reply_text("❌ Не указаны карты для обмена!")
        return
    
    # Сохраняем предложение обмена
    trade_id = create_trade(user_id, target_user_id, user_cards, [])
    
    # Создаем клавиатуру для принятия/отклонения обмена
    keyboard = [
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"trade_accept_{trade_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"trade_decline_{trade_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем сообщение с предложением обмена
    trade_text = f"🤝 **Предложение обмена**\n\n"
    trade_text += f"От: {update.effective_user.first_name}\n"
    trade_text += f"Кому: {target_username}\n\n"
    trade_text += "**Предлагаемые карты:**\n"
    
    for card in user_cards:
        original_card = get_card_by_id(card["card_id"])
        if original_card:
            trade_text += f"• {original_card['name']} ({original_card['rarity']}) - {original_card['points']} очков\n"
    
    trade_text += f"\nID обмена: {trade_id}"
    
    await update.message.reply_text(
        f"✅ Предложение обмена отправлено пользователю {target_username}!\n"
        f"ID обмена: {trade_id}"
    )
    
    # Отправляем предложение целевому пользователю
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=trade_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text("❌ Не удалось отправить предложение обмена. Пользователь, возможно, не начал диалог с ботом.")
        logger.error(f"Error sending trade offer: {e}")

async def handle_trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий с обменом"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    action = query.data
    
    if action.startswith("trade_accept_"):
        trade_id = int(action.replace("trade_accept_", ""))
        await accept_trade(query, context, user_id, trade_id)
    elif action.startswith("trade_decline_"):
        trade_id = int(action.replace("trade_decline_", ""))
        await decline_trade(query, context, trade_id)

async def accept_trade(query, context, user_id, trade_id):
    """Принять обмен"""
    trade = get_trade(trade_id)
    
    if not trade:
        await query.edit_message_text("❌ Обмен не найден!")
        return
    
    if trade['user2_id'] != user_id:
        await query.edit_message_text("❌ Этот обмен не для вас!")
        return
    
    if trade['status'] != 'pending':
        await query.edit_message_text("❌ Этот обмен уже завершен!")
        return
    
    # Получаем данные пользователей
    user_data = load_user_data()
    user1_id = trade['user1_id']
    user2_id = trade['user2_id']
    
    # Проверяем, что карты все еще у пользователей
    user1_cards = json.loads(trade['user1_cards'])
    user2_cards = json.loads(trade['user2_cards'])
    
    # Проверяем карты первого пользователя
    for card in user1_cards:
        if card not in user_data[user1_id]["inventory"]:
            await query.edit_message_text("❌ У одного из пользователей больше нет указанных карт!")
            return
    
    # Обмен картами
    for card in user1_cards:
        user_data[user1_id]["inventory"].remove(card)
        user_data[user1_id]["total_points"] -= card["points"]
        
        # Добавляем карту второму пользователю
        user_data[user2_id]["inventory"].append({
            "card_id": card["card_id"],
            "name": card["name"],
            "rarity": card["rarity"],
            "points": card["points"],
            "acquired": datetime.now(timezone.utc).isoformat(),
            "from_trade": True
        })
        user_data[user2_id]["total_points"] += card["points"]
    
    # Если есть карты от второго пользователя, обмениваем и их
    for card in user2_cards:
        user_data[user2_id]["inventory"].remove(card)
        user_data[user2_id]["total_points"] -= card["points"]
        
        # Добавляем карту первому пользователю
        user_data[user1_id]["inventory"].append({
            "card_id": card["card_id"],
            "name": card["name"],
            "rarity": card["rarity"],
            "points": card["points"],
            "acquired": datetime.now(timezone.utc).isoformat(),
            "from_trade": True
        })
        user_data[user1_id]["total_points"] += card["points"]
    
    # Сохраняем изменения и обновляем статус обмена
    save_user_data(user_data)
    update_trade_status(trade_id, "completed")
    
    # Уведомляем пользователей
    await query.edit_message_text("✅ Обмен успешно завершен!")
    
    try:
        await context.bot.send_message(
            chat_id=user1_id,
            text=f"✅ Ваш обмен #{trade_id} был принят и завершен!"
        )
    except Exception as e:
        logger.error(f"Error notifying user about trade: {e}")

async def decline_trade(query, context, trade_id):
    """Отклонить обмен"""
    trade = get_trade(trade_id)
    
    if not trade:
        await query.edit_message_text("❌ Обмен не найден!")
        return
    
    update_trade_status(trade_id, "declined")
    
    await query.edit_message_text("❌ Обмен отклонен.")
    
    # Уведомляем другого пользователя
    try:
        user1_id = trade['user1_id']
        await context.bot.send_message(
            chat_id=user1_id,
            text=f"❌ Ваш обмен #{trade_id} был отклонен."
        )
    except Exception as e:
        logger.error(f"Error notifying user about declined trade: {e}")

# ==================== МИНИ-ИГРЫ ====================
async def show_minigames(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню мини-игр"""
    keyboard = [
        [InlineKeyboardButton("🎰 Рулетка", callback_data="minigame_roulette")],
        [InlineKeyboardButton("🎯 Угадай редкость", callback_data="minigame_guess")],
        [InlineKeyboardButton("🔙 Назад", callback_data="minigame_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 **Мини-игры**\n\n"
        "Выберите игру:\n"
        "• 🎰 **Рулетка** - рискните картой для шанса получить лучшую\n"
        "• 🎯 **Угадай редкость** - угадайте редкость карты для удвоения очков\n\n"
        "Используйте кнопки ниже:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_minigame_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора мини-игры"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "minigame_back":
        await query.edit_message_text("🔙 Возврат в главное меню")
        return
    elif action == "minigame_roulette":
        await start_roulette(query, context)
    elif action == "minigame_guess":
        await start_guess_rarity(query, context)

async def start_roulette(query, context):
    """Начать игру в рулетку"""
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data or not user_data[user_id]["inventory"]:
        await query.edit_message_text("❌ У вас нет карт для игры в рулетку!")
        return
    
    # Получаем карты пользователя, которые можно использовать
    user_cards = user_data[user_id]["inventory"]
    
    # Создаем клавиатуру с картами
    keyboard = []
    for card in user_cards[:10]:  # Ограничиваем показ 10 карт
        original_card = get_card_by_id(card["card_id"])
        if original_card:
            button_text = f"{original_card['emoji']} {original_card['name']} ({card['points']} очков)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"roulette_{card['card_id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="minigame_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎰 **Рулетка**\n\n"
        "Правила:\n"
        "• Выберите карту для риска\n"
        "• Шанс выигрыша: 40%\n"
        "• При выигрыше: получите карту более высокой редкости\n"
        "• При проигрыше: теряете выбранную карту\n\n"
        "**Выберите карту для игры:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_roulette_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора карты для рулетки"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    action = query.data
    
    if action == "minigame_back":
        await query.edit_message_text("🔙 Возврат к выбору игры")
        return
    
    if action.startswith("roulette_"):
        card_id = float(action.replace("roulette_", ""))
        await play_roulette(query, context, user_id, card_id)

async def play_roulette(query, context, user_id, card_id):
    """Игра в рулетку"""
    user_data = load_user_data()
    
    # Находим выбранную карту
    user_card = next((card for card in user_data[user_id]["inventory"] if card["card_id"] == card_id), None)
    if not user_card:
        await query.edit_message_text("❌ Карта не найдена!")
        return
    
    original_card = get_card_by_id(card_id)
    if not original_card:
        await query.edit_message_text("❌ Ошибка при получении информации о карте!")
        return
    
    # Определяем шанс выигрыша
    win_chance = MINIGAME_CONFIG["roulette"]["win_chance"]
    win = random.random() * 100 <= win_chance
    
    if win:
        # ВЫИГРЫШ - получаем карту более высокой редкости
        rarity_order = ["Редкая", "Сверхредкая", "Эпическая", "Мифическая", "Легендарная", "Секретная", "Эксклюзивная"]
        current_rarity_index = rarity_order.index(original_card["rarity"])
        
        if current_rarity_index < len(rarity_order) - 1:
            next_rarity = rarity_order[current_rarity_index + 1]
            new_card = get_random_card_by_rarity(next_rarity)
            
            if new_card:
                # Удаляем старую карту
                user_data[user_id]["inventory"].remove(user_card)
                user_data[user_id]["total_points"] -= user_card["points"]
                
                # Добавляем новую карту
                user_data[user_id]["inventory"].append({
                    "card_id": new_card["id"],
                    "name": new_card["name"],
                    "rarity": new_card["rarity"],
                    "points": new_card["points"],
                    "acquired": datetime.now(timezone.utc).isoformat(),
                    "from_roulette": True
                })
                user_data[user_id]["total_points"] += new_card["points"]
                
                save_user_data(user_data)
                
                result_text = (
                    f"🎉 **ВЫ ВЫИГРАЛИ!** 🎉\n\n"
                    f"Вы рискнули: {original_card['name']}\n"
                    f"И получили: {new_card['name']}\n"
                    f"📈 Улучшение: {original_card['rarity']} → {new_card['rarity']}\n"
                    f"⭐ Новые очки: {new_card['points']}\n"
                    f"🎲 Шанс выигрыша: {win_chance}%"
                )
                
                try:
                    with open(new_card['image'], 'rb') as photo:
                        await query.message.reply_photo(photo=photo, caption=result_text, parse_mode='Markdown')
                except FileNotFoundError:
                    await query.message.reply_text(f"❌ Ошибка: изображение не найдено\n\n{result_text}", parse_mode='Markdown')
                
                await query.edit_message_text("🎰 Рулетка завершена!")
            else:
                await query.edit_message_text("❌ Ошибка при создании новой карты!")
        else:
            await query.edit_message_text("🎉 У вас уже самая редкая карта! Вы получаете бонусные очки!")
            user_data[user_id]["total_points"] += original_card["points"] * 2
            save_user_data(user_data)
    
    else:
        # ПРОИГРЫШ - теряем карту
        user_data[user_id]["inventory"].remove(user_card)
        user_data[user_id]["total_points"] -= user_card["points"]
        save_user_data(user_data)
        
        await query.edit_message_text(
            f"💥 **ВЫ ПРОИГРАЛИ!** 💥\n\n"
            f"Вы потеряли: {original_card['name']}\n"
            f"Редкость: {original_card['rarity']}\n"
            f"Потеряно очков: {original_card['points']}\n"
            f"🎲 Шанс выигрыша был: {win_chance}%\n\n"
            f"Не расстраивайтесь, попробуйте еще раз!",
            parse_mode='Markdown'
        )

async def start_guess_rarity(query, context):
    """Начать игру 'Угадай редкость'"""
    user_id = str(query.from_user.id)
    
    # Выбираем случайную карту
    card = get_random_card()
    if not card:
        await query.edit_message_text("❌ Ошибка при получении карты!")
        return
    
    # Сохраняем карту в контексте пользователя
    context.user_data["guess_card"] = card
    context.user_data["guess_start_time"] = datetime.now(timezone.utc)
    
    # Создаем клавиатуру с вариантами редкостей
    keyboard = []
    rarities = list(RARITY_GROUPS.keys()) + list(EVENT_CARDS.keys())
    
    for rarity in rarities[:6]:  # Ограничиваем 6 вариантами
        emoji = RARITY_GROUPS.get(rarity, {}).get("emoji") or EVENT_CARDS.get(rarity, {}).get("emoji", "❓")
        keyboard.append([InlineKeyboardButton(f"{emoji} {rarity}", callback_data=f"guess_{rarity}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Показываем карту (без информации о редкости)
    try:
        with open(card['image'], 'rb') as photo:
            caption = "🎯 **Угадай редкость!**\n\nКакой редкости эта карта?\nУ вас есть 30 секунд!"
            await query.message.reply_photo(photo=photo, caption=caption, reply_markup=reply_markup, parse_mode='Markdown')
    except FileNotFoundError:
        await query.message.reply_text(
            f"🎯 **Угадай редкость!**\n\n"
            f"Карта: {card['name']}\n"
            f"Какой редкости эта карта?\n\n"
            f"У вас есть 30 секунд!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    await query.edit_message_text("🎯 Игра началась! Смотрите следующее сообщение.")

async def handle_guess_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка угадывания редкости"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    action = query.data
    
    if not action.startswith("guess_"):
        return
    
    guessed_rarity = action.replace("guess_", "")
    card = context.user_data.get("guess_card")
    start_time = context.user_data.get("guess_start_time")
    
    if not card or not start_time:
        await query.edit_message_text("❌ Время вышло или игра не начата!")
        return
    
    # Проверяем время
    time_elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    if time_elapsed > MINIGAME_CONFIG["guess_rarity"]["time_limit"]:
        await query.edit_message_text("⏰ Время вышло! Вы не успели ответить.")
        return
    
    # Проверяем ответ
    if guessed_rarity == card["rarity"]:
        # ПРАВИЛЬНЫЙ ОТВЕТ - награда
        user_data = load_user_data()
        if user_id not in user_data:
            user_data[user_id] = {
                "inventory": [], 
                "total_points": 0, 
                "last_used": None, 
                "used_promocodes": [],
                "daily_streak": 0,
                "last_daily": None,
                "profile_data": {"title": "Новичок", "frame": "Стандартная", "bio": ""}
            }
        
        reward_points = card["points"] * MINIGAME_CONFIG["guess_rarity"]["reward_multiplier"]
        user_data[user_id]["total_points"] += reward_points
        save_user_data(user_data)
        
        result_text = (
            f"🎉 **ПРАВИЛЬНО!** 🎉\n\n"
            f"Карта: {card['name']}\n"
            f"Редкость: {card['rarity']} {card['emoji']}\n"
            f"⭐ Вы заработали: {reward_points} очков!\n"
            f"⏱️ Время ответа: {time_elapsed:.1f} сек."
        )
    else:
        # НЕПРАВИЛЬНЫЙ ОТВЕТ
        result_text = (
            f"❌ **НЕПРАВИЛЬНО!**\n\n"
            f"Карта: {card['name']}\n"
            f"Правильная редкость: {card['rarity']} {card['emoji']}\n"
            f"Ваш ответ: {guessed_rarity}\n"
            f"⏱️ Время ответа: {time_elapsed:.1f} сек.\n\n"
            f"Попробуйте еще раз!"
        )
    
    # Показываем карту с полной информацией
    try:
        with open(card['image'], 'rb') as photo:
            full_caption = (
                f"🎴 {card['name']}\n"
                f"{card['emoji']} Редкость: {card['rarity']}\n"
                f"⭐ Очки: {card['points']}\n\n"
                f"{result_text}"
            )
            await query.message.reply_photo(photo=photo, caption=full_caption, parse_mode='Markdown')
    except FileNotFoundError:
        await query.message.reply_text(f"❌ Ошибка: изображение не найдено\n\n{result_text}", parse_mode='Markdown')
    
    await query.edit_message_text("🎯 Игра завершена!")
    
    # Очищаем данные игры
    context.user_data.pop("guess_card", None)
    context.user_data.pop("guess_start_time", None)

# ==================== КАСТОМНЫЕ ПРОФИЛИ ====================
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль пользователя"""
    user_id = str(update.effective_user.id)
    
    # Если указан username, ищем этого пользователя
    target_user_id = user_id
    if context.args:
        username = context.args[0].replace('@', '')
        user_data = load_user_data()
        
        # В реальном боте нужно получать user_id по username из Telegram API
        # Здесь используем простой поиск по существующим пользователям
        for uid, data in user_data.items():
            if username.lower() in uid.lower():
                target_user_id = uid
                break
    
    user_data = load_user_data()
    
    if target_user_id not in user_data:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    
    user_info = user_data[target_user_id]
    profile_data = user_info.get("profile_data", {"title": "Новичок", "frame": "Стандартная", "bio": ""})
    
    # Получаем статистику
    total_cards = len(user_info["inventory"])
    total_points = user_info["total_points"]
    daily_streak = user_info.get("daily_streak", 0)
    
    # Считаем карты по редкостям
    rarity_count = {}
    for card in user_info["inventory"]:
        rarity = card["rarity"]
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    
    # Формируем профиль
    title = profile_data.get("title", "Новичок")
    frame = profile_data.get("frame", "Стандартная")
    bio = profile_data.get("bio", "Этот пользователь еще не настроил свой профиль.")
    
    title_emoji = PROFILE_TITLES.get(title, {}).get("emoji", "👤")
    frame_color = PROFILE_FRAMES.get(frame, {}).get("color", "⚪")
    
    profile_text = (
        f"{frame_color}┏━━━━━━━━━━━━━━━━━━━━┓\n"
        f"{frame_color}┃      **ПРОФИЛЬ**      ┃\n"
        f"{frame_color}┣━━━━━━━━━━━━━━━━━━━━┫\n"
        f"{frame_color}┃ {title_emoji} **{title}**\n"
        f"{frame_color}┃ 💬 {bio}\n"
        f"{frame_color}┣━━━━━━━━━━━━━━━━━━━━┫\n"
        f"{frame_color}┃ 📊 **Статистика:**\n"
        f"{frame_color}┃ 📚 Карточек: {total_cards}\n"
        f"{frame_color}┃ ⭐ Очков: {total_points}\n"
        f"{frame_color}┃ 🔥 Серия: {daily_streak} дней\n"
        f"{frame_color}┣━━━━━━━━━━━━━━━━━━━━┫\n"
        f"{frame_color}┃ 🎴 **Коллекция:**\n"
    )
    
    # Добавляем информацию по редкостям
    for rarity in RARITY_GROUPS:
        if rarity in rarity_count:
            emoji = RARITY_GROUPS[rarity]["emoji"]
            profile_text += f"{frame_color}┃ {emoji} {rarity}: {rarity_count[rarity]}\n"
    
    # Добавляем информацию по событиям
    for event_config in EVENTS_CONFIG.values():
        event_key = event_config["key"]
        if event_key in rarity_count:
            emoji = event_config["emoji"]
            profile_text += f"{frame_color}┃ {emoji} {event_key}: {rarity_count[event_key]}\n"
    
    profile_text += f"{frame_color}┗━━━━━━━━━━━━━━━━━━━━┛"
    
    # Создаем клавиатуру для управления профилем (только для своего профиля)
    keyboard = []
    if target_user_id == user_id:
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить био", callback_data="profile_edit_bio")],
            [InlineKeyboardButton("🎖️ Выбрать титул", callback_data="profile_select_title")],
            [InlineKeyboardButton("🖼️ Выбрать рамку", callback_data="profile_select_frame")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="profile_close")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий с профилем"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    action = query.data
    
    if action == "profile_close":
        await query.edit_message_text("👤 Профиль закрыт")
        return
    elif action == "profile_edit_bio":
        await query.edit_message_text(
            "✏️ **Изменение био**\n\n"
            "Введите новое описание для вашего профиля (максимум 100 символов):\n\n"
            "Отправьте /cancel для отмены."
        )
        context.user_data["awaiting_bio"] = True
        return
    elif action == "profile_select_title":
        await show_title_selection(query, context)
    elif action == "profile_select_frame":
        await show_frame_selection(query, context)
    elif action.startswith("profile_set_title_"):
        title = action.replace("profile_set_title_", "")
        await set_profile_title(query, context, user_id, title)
    elif action.startswith("profile_set_frame_"):
        frame = action.replace("profile_set_frame_", "")
        await set_profile_frame(query, context, user_id, frame)

async def show_title_selection(query, context):
    """Показать выбор титулов"""
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        await query.edit_message_text("❌ Пользователь не найден!")
        return
    
    user_info = user_data[user_id]
    current_title = user_info.get("profile_data", {}).get("title", "Новичок")
    
    # Создаем клавиатуру с доступными титулами
    keyboard = []
    for title, title_info in PROFILE_TITLES.items():
        emoji = title_info["emoji"]
        
        # Проверяем, доступен ли титул
        available = check_title_availability(user_info, title_info["requirement"])
        
        if available:
            button_text = f"{emoji} {title}"
            if title == current_title:
                button_text += " ✅"
        else:
            button_text = f"{emoji} {title} 🔒"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"profile_set_title_{title}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="profile_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎖️ **Выбор титула**\n\n"
        "✅ - текущий титул\n"
        "🔒 - недоступен (требования не выполнены)\n\n"
        "Выберите титул:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_frame_selection(query, context):
    """Показать выбор рамок"""
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        await query.edit_message_text("❌ Пользователь не найден!")
        return
    
    user_info = user_data[user_id]
    current_frame = user_info.get("profile_data", {}).get("frame", "Стандартная")
    
    # Создаем клавиатуру с доступными рамками
    keyboard = []
    for frame, frame_info in PROFILE_FRAMES.items():
        color = frame_info["color"]
        
        # Проверяем, доступна ли рамка
        available = check_frame_availability(user_info, frame_info["requirement"])
        
        if available:
            button_text = f"{color} {frame}"
            if frame == current_frame:
                button_text += " ✅"
        else:
            button_text = f"{color} {frame} 🔒"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"profile_set_frame_{frame}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="profile_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🖼️ **Выбор рамки**\n\n"
        "✅ - текущая рамка\n"
        "🔒 - недоступна (требования не выполнены)\n\n"
        "Выберите рамку:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def check_title_availability(user_info, requirement):
    """Проверить доступность титула"""
    total_cards = len(user_info["inventory"])
    total_points = user_info["total_points"]
    
    if requirement == "default":
        return True
    elif requirement == "total_cards_50":
        return total_cards >= 50
    elif requirement == "total_cards_100":
        return total_cards >= 100
    elif requirement == "total_cards_200":
        return total_cards >= 200
    elif requirement == "total_cards_500":
        return total_cards >= 500
    elif requirement == "total_points_100000":
        return total_points >= 100000
    elif requirement == "all_rare_cards":
        # Проверяем, есть ли все карты редкости "Редкая"
        rare_cards = [card for card in user_info["inventory"] if card["rarity"] == "Редкая"]
        return len(rare_cards) >= len(RARITY_GROUPS["Редкая"]["cards"])
    elif requirement == "all_event_cards":
        # Проверяем, есть ли карты из всех событий
        event_cards_found = 0
        for event_key in EVENT_CARDS:
            if any(card["rarity"] == event_key for card in user_info["inventory"]):
                event_cards_found += 1
        return event_cards_found >= len(EVENT_CARDS)
    
    return False

def check_frame_availability(user_info, requirement):
    """Проверить доступность рамки"""
    total_cards = len(user_info["inventory"])
    total_points = user_info["total_points"]
    
    if requirement == "default":
        return True
    elif requirement == "total_points_50000":
        return total_points >= 50000
    elif requirement == "total_points_200000":
        return total_points >= 200000
    elif requirement == "total_cards_300":
        return total_cards >= 300
    elif requirement == "all_rarity_cards":
        # Проверяем, есть ли хотя бы одна карта каждой редкости
        rarities_found = set(card["rarity"] for card in user_info["inventory"])
        return len(rarities_found) >= len(RARITY_GROUPS)
    elif requirement == "special_achievement":
        # Специальное достижение - есть хотя бы одна карта каждого события
        event_cards_found = 0
        for event_key in EVENT_CARDS:
            if any(card["rarity"] == event_key for card in user_info["inventory"]):
                event_cards_found += 1
        return event_cards_found >= len(EVENT_CARDS)
    
    return False

async def set_profile_title(query, context, user_id, title):
    """Установить титул профиля"""
    user_data = load_user_data()
    
    if user_id not in user_data:
        await query.edit_message_text("❌ Пользователь не найден!")
        return
    
    # Проверяем доступность титула
    title_info = PROFILE_TITLES.get(title)
    if not title_info:
        await query.edit_message_text("❌ Титул не найден!")
        return
    
    if not check_title_availability(user_data[user_id], title_info["requirement"]):
        await query.edit_message_text("❌ Этот титул вам еще недоступен!")
        return
    
    # Устанавливаем титул
    if "profile_data" not in user_data[user_id]:
        user_data[user_id]["profile_data"] = {}
    
    user_data[user_id]["profile_data"]["title"] = title
    save_user_data(user_data)
    
    await query.edit_message_text(f"✅ Титул изменен на: {title_info['emoji']} {title}")

async def set_profile_frame(query, context, user_id, frame):
    """Установить рамку профиля"""
    user_data = load_user_data()
    
    if user_id not in user_data:
        await query.edit_message_text("❌ Пользователь не найден!")
        return
    
    # Проверяем доступность рамки
    frame_info = PROFILE_FRAMES.get(frame)
    if not frame_info:
        await query.edit_message_text("❌ Рамка не найдена!")
        return
    
    if not check_frame_availability(user_data[user_id], frame_info["requirement"]):
        await query.edit_message_text("❌ Эта рамка вам еще недоступна!")
        return
    
    # Устанавливаем рамку
    if "profile_data" not in user_data[user_id]:
        user_data[user_id]["profile_data"] = {}
    
    user_data[user_id]["profile_data"]["frame"] = frame
    save_user_data(user_data)
    
    await query.edit_message_text(f"✅ Рамка изменена на: {frame_info['color']} {frame}")

async def handle_bio_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода био"""
    user_id = str(update.effective_user.id)
    
    if not context.user_data.get("awaiting_bio"):
        return
    
    bio_text = update.message.text
    
    if bio_text.startswith('/'):
        if bio_text == '/cancel':
            await update.message.reply_text("❌ Изменение био отменено.")
            context.user_data["awaiting_bio"] = False
            return
        return
    
    if len(bio_text) > 100:
        await update.message.reply_text("❌ Описание слишком длинное! Максимум 100 символов.")
        return
    
    # Сохраняем био
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {
            "inventory": [], 
            "total_points": 0, 
            "last_used": None, 
            "used_promocodes": [],
            "daily_streak": 0,
            "last_daily": None,
            "profile_data": {"title": "Новичок", "frame": "Стандартная", "bio": ""}
        }
    
    if "profile_data" not in user_data[user_id]:
        user_data[user_id]["profile_data"] = {}
    
    user_data[user_id]["profile_data"]["bio"] = bio_text
    save_user_data(user_data)
    
    await update.message.reply_text("✅ Био успешно обновлено!")
    context.user_data["awaiting_bio"] = False

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================
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
    
    # Создаем клавиатуру с новыми функциями
    keyboard = [
        [InlineKeyboardButton("🎴 Получить карту", callback_data="get_card_main")],
        [InlineKeyboardButton("📚 Инвентарь", callback_data="inventory_main")],
        [InlineKeyboardButton("🛠️ Крафт", callback_data="craft_main"), InlineKeyboardButton("🎮 Мини-игры", callback_data="minigames_main")],
        [InlineKeyboardButton("🤝 Обмен", callback_data="trade_main"), InlineKeyboardButton("👤 Профиль", callback_data="profile_main")],
        [InlineKeyboardButton("🎁 Ежедневная награда", callback_data="daily_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎴 **Добро пожаловать в коллекцию карточек!**\n\n"
        f"{event_info}"
        "📖 **Доступные команды:**\n"
        "/getcard - Получить случайную карточку\n"
        "/inventory - Показать вашу коллекцию\n"
        "/craft - Мастерская крафта\n"
        "/daily - Ежедневная награда\n"
        "/trade - Обмен карточками\n"
        "/minigames - Мини-игры\n"
        "/profile - Ваш профиль\n"
        "/promo <код> - Активировать промокод\n"
        "/event - Информация о событии\n\n"
        f"⏰ **Кулдаун:** {COOLDOWN_MINUTES} минут\n\n"
        f"{rarity_info}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка главного меню"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "get_card_main":
        await get_card_from_callback(query, context)
    elif action == "inventory_main":
        await show_inventory_from_callback(query, context)
    elif action == "craft_main":
        await show_craft_menu_from_callback(query, context)
    elif action == "minigames_main":
        await show_minigames_from_callback(query, context)
    elif action == "trade_main":
        await start_trade_from_callback(query, context)
    elif action == "profile_main":
        await show_profile_from_callback(query, context)
    elif action == "daily_main":
        await daily_reward_from_callback(query, context)

async def get_card_from_callback(query, context):
    """Получить карту из callback"""
    user_id = str(query.from_user.id)
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
                
            await query.message.reply_text(
                f"⏳ Следующая карточка будет доступна через {time_message}"
            )
            await query.edit_message_text("🎴 Получение карты")
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
            await query.message.reply_photo(photo=photo, caption=caption, parse_mode='Markdown')
    except FileNotFoundError:
        await query.message.reply_text(f"❌ Ошибка: изображение {card['image']} не найдено")

    if user_id not in user_data:
        user_data[user_id] = {
            "inventory": [], 
            "total_points": 0, 
            "last_used": None, 
            "used_promocodes": [],
            "daily_streak": 0,
            "last_daily": None,
            "profile_data": {"title": "Новичок", "frame": "Стандартная", "bio": ""}
        }
    
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
    await query.edit_message_text("🎴 Карта получена!")

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

async def show_inventory_from_callback(query, context):
    """Показать инвентарь из callback"""
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
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_rarity_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать карточки определенной редкости"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    rarity = query.data.replace('rarity_', '')
    
    user_data = load_user_data()
    if user_id not in user_data:
        await query.edit_message_text("❌ Пользователь не найден!")
        return
    
    # Фильтруем карточки по редкости
    rarity_cards = [card for card in user_data[user_id]["inventory"] if card["rarity"] == rarity]
    
    if not rarity_cards:
        await query.edit_message_text(f"❌ У вас нет карточек редкости {rarity}!")
        return
    
    # Показываем первую карточку
    await show_card_navigation(query, context, rarity, 0)

async def show_card_navigation(query, context, rarity, index):
    """Показать навигацию по карточкам"""
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    rarity_cards = [card for card in user_data[user_id]["inventory"] if card["rarity"] == rarity]
    
    if index >= len(rarity_cards):
        index = 0
    
    card = rarity_cards[index]
    original_card = get_card_by_id(card["card_id"])
    
    if not original_card:
        await query.edit_message_text("❌ Ошибка при загрузке карточки!")
        return
    
    # Создаем клавиатуру навигации
    keyboard = []
    
    if len(rarity_cards) > 1:
        nav_buttons = []
        if index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_{rarity}_{index-1}"))
        if index < len(rarity_cards) - 1:
            nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"nav_{rarity}_{index+1}"))
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Назад к редкостям", callback_data="back_to_rarities")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    card_text = (
        f"🎴 **{original_card['name']}**\n"
        f"{original_card['emoji']} **Редкость:** {original_card['rarity']}\n"
        f"⭐ **Очки:** {original_card['points']}\n"
        f"📅 **Получена:** {card['acquired'][:10]}\n"
        f"🔢 **Позиция:** {index + 1}/{len(rarity_cards)}"
    )
    
    try:
        with open(original_card['image'], 'rb') as photo:
            await query.edit_message_media(
                media=InputMediaPhoto(media=photo, caption=card_text, parse_mode='Markdown'),
                reply_markup=reply_markup
            )
    except FileNotFoundError:
        await query.edit_message_text(
            f"❌ Ошибка: изображение не найдено\n\n{card_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка навигации по карточкам"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "back_to_rarities":
        await show_inventory_from_callback(query, context)
        return
    
    if data.startswith("nav_"):
        parts = data.split('_')
        if len(parts) >= 3:
            rarity = parts[1]
            index = int(parts[2])
            await show_card_navigation(query, context, rarity, index)

async def show_craft_menu_from_callback(query, context):
    """Показать меню крафта из callback"""
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data or not user_data[user_id]["inventory"]:
        await query.edit_message_text("📭 Ваша коллекция пуста! Сначала получите карточки.")
        return
    
    keyboard = []
    for recipe_name, recipe in CRAFT_RECIPES.items():
        can_craft = True
        for ingredient in recipe["ingredients"]:
            user_cards = [card for card in user_data[user_id]["inventory"] if card["rarity"] == ingredient["rarity"]]
            if len(user_cards) < ingredient["count"]:
                can_craft = False
                break
        
        button_text = f"{recipe['description']}"
        if not can_craft:
            button_text += " ❌"
        else:
            button_text += " ✅"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"craft_{recipe_name}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="craft_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🛠️ **Мастерская крафта**\n\n"
        "Выберите рецепт для создания карточек более высокой редкости:\n"
        "✅ - можно скрафтить\n"
        "❌ - недостаточно карт\n\n"
        "Шансы успеха указаны в описании.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_minigames_from_callback(query, context):
    """Показать мини-игры из callback"""
    keyboard = [
        [InlineKeyboardButton("🎰 Рулетка", callback_data="minigame_roulette")],
        [InlineKeyboardButton("🎯 Угадай редкость", callback_data="minigame_guess")],
        [InlineKeyboardButton("🔙 Назад", callback_data="minigame_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎮 **Мини-игры**\n\n"
        "Выберите игру:\n"
        "• 🎰 **Рулетка** - рискните картой для шанса получить лучшую\n"
        "• 🎯 **Угадай редкость** - угадайте редкость карты для удвоения очков\n\n"
        "Используйте кнопки ниже:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def start_trade_from_callback(query, context):
    """Начать обмен из callback"""
    await query.edit_message_text(
        "🤝 **Обмен карточками**\n\n"
        "Использование:\n"
        "/trade @username card_id1,card_id2...\n\n"
        "Пример:\n"
        "/trade @username 2.1,2.2,2.3\n\n"
        "Чтобы посмотреть ID карт, используйте /inventory"
    )

async def show_profile_from_callback(query, context):
    """Показать профиль из callback"""
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        await query.edit_message_text("❌ Пользователь не найден!")
        return
    
    user_info = user_data[user_id]
    profile_data = user_info.get("profile_data", {"title": "Новичок", "frame": "Стандартная", "bio": ""})
    
    total_cards = len(user_info["inventory"])
    total_points = user_info["total_points"]
    daily_streak = user_info.get("daily_streak", 0)
    
    rarity_count = {}
    for card in user_info["inventory"]:
        rarity = card["rarity"]
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    
    title = profile_data.get("title", "Новичок")
    frame = profile_data.get("frame", "Стандартная")
    bio = profile_data.get("bio", "Этот пользователь еще не настроил свой профиль.")
    
    title_emoji = PROFILE_TITLES.get(title, {}).get("emoji", "👤")
    frame_color = PROFILE_FRAMES.get(frame, {}).get("color", "⚪")
    
    profile_text = (
        f"{frame_color}┏━━━━━━━━━━━━━━━━━━━━┓\n"
        f"{frame_color}┃      **ПРОФИЛЬ**      ┃\n"
        f"{frame_color}┣━━━━━━━━━━━━━━━━━━━━┫\n"
        f"{frame_color}┃ {title_emoji} **{title}**\n"
        f"{frame_color}┃ 💬 {bio}\n"
        f"{frame_color}┣━━━━━━━━━━━━━━━━━━━━┫\n"
        f"{frame_color}┃ 📊 **Статистика:**\n"
        f"{frame_color}┃ 📚 Карточек: {total_cards}\n"
        f"{frame_color}┃ ⭐ Очков: {total_points}\n"
        f"{frame_color}┃ 🔥 Серия: {daily_streak} дней\n"
        f"{frame_color}┣━━━━━━━━━━━━━━━━━━━━┫\n"
        f"{frame_color}┃ 🎴 **Коллекция:**\n"
    )
    
    for rarity in RARITY_GROUPS:
        if rarity in rarity_count:
            emoji = RARITY_GROUPS[rarity]["emoji"]
            profile_text += f"{frame_color}┃ {emoji} {rarity}: {rarity_count[rarity]}\n"
    
    for event_config in EVENTS_CONFIG.values():
        event_key = event_config["key"]
        if event_key in rarity_count:
            emoji = event_config["emoji"]
            profile_text += f"{frame_color}┃ {emoji} {event_key}: {rarity_count[event_key]}\n"
    
    profile_text += f"{frame_color}┗━━━━━━━━━━━━━━━━━━━━┛"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить био", callback_data="profile_edit_bio")],
        [InlineKeyboardButton("🎖️ Выбрать титул", callback_data="profile_select_title")],
        [InlineKeyboardButton("🖼️ Выбрать рамку", callback_data="profile_select_frame")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="profile_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

async def daily_reward_from_callback(query, context):
    """Ежедневная награда из callback"""
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {
            "inventory": [], 
            "total_points": 0, 
            "last_used": None, 
            "used_promocodes": [],
            "daily_streak": 0,
            "last_daily": None,
            "profile_data": {"title": "Новичок", "frame": "Стандартная", "bio": ""}
        }
    
    now = datetime.now(timezone.utc)
    last_daily = user_data[user_id].get("last_daily")
    
    if last_daily:
        last_daily_date = datetime.fromisoformat(last_daily.replace('Z', '+00:00'))
        if last_daily_date.tzinfo is None:
            last_daily_date = last_daily_date.replace(tzinfo=timezone.utc)
        
        time_since_last_daily = now - last_daily_date
        if time_since_last_daily < timedelta(hours=20):
            next_daily = last_daily_date + timedelta(hours=20)
            time_left = next_daily - now
            
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            
            await query.edit_message_text(
                f"⏳ Следующая ежедневная награда будет доступна через {hours}ч {minutes}м\n"
                f"Текущая серия: {user_data[user_id].get('daily_streak', 0)} дней"
            )
            return
        
        if time_since_last_daily > timedelta(hours=44):
            user_data[user_id]["daily_streak"] = 0
    
    user_data[user_id]["daily_streak"] = user_data[user_id].get("daily_streak", 0) + 1
    streak = user_data[user_id]["daily_streak"]
    
    day = ((streak - 1) % 7) + 1
    reward_info = DAILY_REWARDS[day]
    
    reward_text = f"🎁 **Ежедневная награда - День {day}**\n\n"
    reward_text += f"📅 Серия: {streak} дней\n\n"
    
    if reward_info["type"] == "points":
        points = reward_info["amount"]
        user_data[user_id]["total_points"] += points
        reward_text += f"💰 Вы получили: {points} очков!\n"
        reward_text += f"📝 {reward_info['description']}"
    
    elif reward_info["type"] == "random_card":
        rarity = reward_info["rarity"]
        card = get_random_card_by_rarity(rarity)
        if card:
            user_data[user_id]["inventory"].append({
                "card_id": card["id"],
                "name": card["name"],
                "rarity": card["rarity"],
                "points": card["points"],
                "acquired": datetime.now(timezone.utc).isoformat(),
                "from_daily": True
            })
            user_data[user_id]["total_points"] += card["points"]
            
            reward_text += f"🎴 Вы получили: {card['name']}\n"
            reward_text += f"{card['emoji']} Редкость: {card['rarity']}\n"
            reward_text += f"⭐ Очки: {card['points']}\n"
            reward_text += f"📝 {reward_info['description']}"
            
            try:
                with open(card['image'], 'rb') as photo:
                    await query.message.reply_photo(photo=photo, caption=reward_text, parse_mode='Markdown')
            except FileNotFoundError:
                await query.message.reply_text(f"❌ Ошибка: изображение не найдено\n\n{reward_text}", parse_mode='Markdown')
        else:
            reward_text += "❌ Ошибка при получении карты!"
            await query.edit_message_text(reward_text, parse_mode='Markdown')
    
    elif reward_info["type"] == "special":
        card = get_random_card_by_rarity("Легендарная")
        if card:
            user_data[user_id]["inventory"].append({
                "card_id": card["id"],
                "name": card["name"],
                "rarity": card["rarity"],
                "points": card["points"],
                "acquired": datetime.now(timezone.utc).isoformat(),
                "from_daily": True
            })
            user_data[user_id]["total_points"] += card["points"]
            
            reward_text += f"🎉 **СУПЕР ПРИЗ!** 🎉\n\n"
            reward_text += f"🎴 Вы получили: {card['name']}\n"
            reward_text += f"{card['emoji']} Редкость: {card['rarity']}\n"
            reward_text += f"⭐ Очки: {card['points']}\n"
            reward_text += f"📝 {reward_info['description']}"
            
            try:
                with open(card['image'], 'rb') as photo:
                    await query.message.reply_photo(photo=photo, caption=reward_text, parse_mode='Markdown')
            except FileNotFoundError:
                await query.message.reply_text(f"❌ Ошибка: изображение не найдено\n\n{reward_text}", parse_mode='Markdown')
        else:
            reward_text += "❌ Ошибка при получении карты!"
            await query.edit_message_text(reward_text, parse_mode='Markdown')
    
    user_data[user_id]["last_daily"] = now.isoformat()
    save_user_data(user_data)
    
    if reward_info["type"] != "random_card" and reward_info["type"] != "special":
        await query.edit_message_text(reward_text, parse_mode='Markdown')

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
        user_data[user_id] = {
            "inventory": [], 
            "total_points": 0, 
            "last_used": None, 
            "used_promocodes": [],
            "daily_streak": 0,
            "last_daily": None,
            "profile_data": {"title": "Новичок", "frame": "Стандартная", "bio": ""}
        }
    
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

async def get_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить карту обычным способом"""
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
        user_data[user_id] = {
            "inventory": [], 
            "total_points": 0, 
            "last_used": None, 
            "used_promocodes": [],
            "daily_streak": 0,
            "last_daily": None,
            "profile_data": {"title": "Новичок", "frame": "Стандартная", "bio": ""}
        }
    
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

# ==================== ЗАПУСК БОТА ====================
if __name__ == "__main__":
    # Инициализация базы данных
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
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getcard", get_card))
    application.add_handler(CommandHandler("inventory", show_inventory))
    application.add_handler(CommandHandler("rarities", show_rarities))
    application.add_handler(CommandHandler("promo", use_promo))
    application.add_handler(CommandHandler("event", show_event_info))
    
    # Новые команды
    application.add_handler(CommandHandler("craft", show_craft_menu))
    application.add_handler(CommandHandler("daily", daily_reward))
    application.add_handler(CommandHandler("trade", start_trade))
    application.add_handler(CommandHandler("minigames", show_minigames))
    application.add_handler(CommandHandler("profile", show_profile))
    
    # Обработчики callback-ов
    application.add_handler(CallbackQueryHandler(handle_main_callback, pattern="^get_card_main|inventory_main|craft_main|minigames_main|trade_main|profile_main|daily_main$"))
    application.add_handler(CallbackQueryHandler(show_rarity_cards, pattern="^rarity_"))
    application.add_handler(CallbackQueryHandler(handle_navigation, pattern="^nav_"))
    application.add_handler(CallbackQueryHandler(show_inventory_from_callback, pattern="^back_to_rarities$"))
    
    # Обработчики крафта
    application.add_handler(CallbackQueryHandler(handle_craft_callback, pattern="^craft_"))
    application.add_handler(CallbackQueryHandler(handle_craft_callback, pattern="^craft_back"))
    
    # Обработчики обмена
    application.add_handler(CallbackQueryHandler(handle_trade_callback, pattern="^trade_"))
    
    # Обработчики мини-игр
    application.add_handler(CallbackQueryHandler(handle_minigame_callback, pattern="^minigame_"))
    application.add_handler(CallbackQueryHandler(handle_roulette_callback, pattern="^roulette_"))
    application.add_handler(CallbackQueryHandler(handle_guess_callback, pattern="^guess_"))
    
    # Обработчики профиля
    application.add_handler(CallbackQueryHandler(handle_profile_callback, pattern="^profile_"))
    
    # Обработчик текстовых сообщений (для био)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bio_input))
    
    logger.info("Бот запущен на Railway...")
    application.run_polling()
