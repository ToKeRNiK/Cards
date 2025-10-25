import os
import json
import random
import logging
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8295319122:AAFGvZ1GFqPv8EkCTQnXjSKzd4dOG8rz1bg')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is not set!")
    exit(1)

COOLDOWN_MINUTES = 15

# Группировка карточек по редкостям
RARITY_GROUPS = {
    "Обычная": {
        "chance": 39,
        "emoji": "⚪",
        "cards": [
            {"id": 1, "name": "Бургер Кинг", "image": "cards/Common/card1.jpg", "points": 10},
            {"id": 2, "name": "Служебное помещение", "image": "cards/Common/card1.1.jpg", "points": 10},
            {"id": 3, "name": "Оператор опять нюхает", "image": "cards/Common/card1.2.jpg", "points": 10},
        ]
    },
    "Редкая": {
        "chance": 25,
        "emoji": "🟢",
        "cards": [
            {"id": 4, "name": "Вкусно и точка", "image": "cards/Rare/card2.jpg", "points": 50},
            {"id": 5, "name": "Два задрота", "image": "cards/Rare/card2.1.jpg", "points": 50},
        ]
    },
    "Сверхредкая": {
        "chance": 15,
        "emoji": "🔵",
        "cards": [
            {"id": 7, "name": "Ярик", "image": "cards/SuperRare/card3.jpg", "points": 200},
            {"id": 8, "name": "УВЗ", "image": "cards/SuperRare/card3.1.jpg", "points": 200},
        ]
    },
    "Эпическая": {
        "chance": 10,
        "emoji": "🟣",
        "cards": [
            {"id": 10, "name": "Михаил Динозавр", "image": "cards/Epic/card4.jpg", "points": 1000},
            {"id": 11, "name": "Стёпа Автомобилист", "image": "cards/Epic/card4.1.jpg", "points": 1000},
        ]
    },
    "Мифическая": {
        "chance": 7,
        "emoji": "🔴",
        "cards": [
            {"id": 13, "name": "Сигма Михаил Медведь", "image": "cards/Mythic/card5.jpg", "points": 5000},
            {"id": 14, "name": "Гриша Шалун", "image": "cards/Mythic/card5.1.jpg", "points": 5000},
            {"id": 15, "name": "ЕВРАЗ", "image": "cards/Mythic/card5.2.jpg", "points": 5000},
        ]
    },
    "Легендарная": {
        "chance": 3,
        "emoji": "🟡",
        "cards": [
            {"id": 16, "name": "Стёпа с фанатами", "image": "cards/Legendary/card6.jpg", "points": 10000},
        ]
    },
    "Секретная": {
        "chance": 1,
        "emoji": "⚫️",
        "cards": [
            {"id": 17, "name": "Который час?", "image": "cards/Secret/card7.jpg", "points": 20000},
            {"id": 18, "name": "Держатель яиц Ярик", "image": "cards/Secret/card7.1.jpg", "points": 30000},
        ]
    },
}

# Функции для работы с данными
def load_user_data():
    """Загрузка данных пользователей"""
    try:
        with open('user_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Конвертируем старые форматы времени
            for user_id, user_info in data.items():
                if 'last_used' in user_info and user_info['last_used']:
                    if user_info['last_used'].endswith('Z'):
                        user_info['last_used'] = user_info['last_used'].replace('Z', '+00:00')
            return data
    except FileNotFoundError:
        logger.info("user_data.json не найден, создаю новый файл")
        return {}
    except json.JSONDecodeError:
        logger.error("Ошибка чтения user_data.json, создаю новый файл")
        return {}

def save_user_data(data):
    """Сохранение данных пользователей"""
    try:
        with open('user_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

def get_utc_now():
    """Получение текущего времени в UTC"""
    return datetime.now(timezone.utc)

def parse_datetime(dt_str):
    """Парсинг строки времени с учетом временных зон"""
    if not dt_str:
        return None
    
    try:
        if dt_str.endswith('Z'):
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(dt_str)
    except ValueError as e:
        logger.error(f"Ошибка парсинга времени {dt_str}: {e}")
        return None

# Получение случайной карточки
def get_random_card():
    """Генерация случайной карточки согласно шансам"""
    roll = random.random() * 100
    current = 0
    
    for rarity, data in RARITY_GROUPS.items():
        current += data["chance"]
        if roll <= current:
            card = random.choice(data["cards"]).copy()
            card.update({
                "rarity": rarity,
                "emoji": data["emoji"],
                "rarity_chance": data["chance"]
            })
            return card
    
    # Fallback - первая карточка из обычных
    rarity = "Обычная"
    data = RARITY_GROUPS[rarity]
    card = random.choice(data["cards"]).copy()
    card.update({
        "rarity": rarity,
        "emoji": data["emoji"],
        "rarity_chance": data["chance"]
    })
    return card

def format_time_remaining(seconds):
    """Форматирование оставшегося времени"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours} часов {minutes} минут {seconds} секунд"
    elif minutes > 0:
        return f"{minutes} минут {seconds} секунд"
    else:
        return f"{seconds} секунд"

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        rarity_info = "🎲 **Шансы редкостей:**\n"
        for rarity, data in RARITY_GROUPS.items():
            emoji = data["emoji"]
            chance = data["chance"]
            card_count = len(data["cards"])
            rarity_info += f"{emoji} {rarity}: {chance}% ({card_count} карточек)\n"
        
        await update.message.reply_text(
            "🎴 **Добро пожаловать в коллекцию карточек!**\n\n"
            "📖 **Доступные команды:**\n"
            "/getcard - Получить случайную карточку\n"
            "/inventory - Показать вашу коллекцию\n"
            "/rarities - Информация о редкостях\n\n"
            f"⏰ **Кулдаун:** {COOLDOWN_MINUTES} минут\n\n"
            f"{rarity_info}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Ошибка в команде /start: {e}")
        await update.message.reply_text("❌ Произошла ошибка при выполнении команды")

async def show_rarities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /rarities"""
    try:
        rarity_info = "🎲 **Шансы редкостей:**\n"
        for rarity, data in RARITY_GROUPS.items():
            emoji = data["emoji"]
            chance = data["chance"]
            card_count = len(data["cards"])
            rarity_info += f"{emoji} {rarity}: {chance}% ({card_count} карточек)\n"
        
        await update.message.reply_text(rarity_info, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка в команде /rarities: {e}")
        await update.message.reply_text("❌ Произошла ошибка при выполнении команды")

async def get_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /getcard"""
    try:
        user_id = str(update.effective_user.id)
        user_data = load_user_data()

        # Проверка кулдауна
        last_used_str = user_data.get(user_id, {}).get('last_used')
        if last_used_str:
            last_used = parse_datetime(last_used_str)
            if last_used:
                current_time = get_utc_now()
                time_passed = current_time - last_used
                cooldown_duration = timedelta(minutes=COOLDOWN_MINUTES)
                
                if time_passed < cooldown_duration:
                    remaining_time = cooldown_duration - time_passed
                    time_message = format_time_remaining(int(remaining_time.total_seconds()))
                    
                    await update.message.reply_text(
                        f"⏳ Следующая карточка будет доступна через {time_message}"
                    )
                    return

        # Генерация карточки
        card = get_random_card()
        
        caption = (
            f"🎴 **Вы получили карточку:** {card['name']}\n"
            f"{card['emoji']} **Редкость:** {card['rarity']}\n"
            f"⭐ **Очки:** {card['points']}\n"
            f"🎲 Шанс редкости: {card['rarity_chance']}%"
        )

        # Отправка карточки
        try:
            if os.path.exists(card['image']):
                with open(card['image'], 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo, 
                        caption=caption, 
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    f"📄 {caption}\n\n"
                    f"⚠️ Изображение временно недоступно",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Ошибка отправки изображения: {e}")
            await update.message.reply_text(
                f"📄 {caption}\n\n"
                f"⚠️ Не удалось загрузить изображение",
                parse_mode='Markdown'
            )

        # Сохранение данных пользователя
        if user_id not in user_data:
            user_data[user_id] = {
                "inventory": [], 
                "total_points": 0,
                "username": update.effective_user.username
            }
        
        user_data[user_id]["inventory"].append({
            "card_id": card["id"],
            "name": card["name"],
            "rarity": card["rarity"],
            "points": card["points"],
            "acquired": get_utc_now().isoformat()
        })
        
        user_data[user_id]["total_points"] += card["points"]
        user_data[user_id]['last_used'] = get_utc_now().isoformat()
        user_data[user_id]['username'] = update.effective_user.username
        
        save_user_data(user_data)
        
        logger.info(f"User {user_id} received card: {card['name']} ({card['rarity']})")

    except Exception as e:
        logger.error(f"Ошибка в команде /getcard: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении карточки")

async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /inventory"""
    try:
        user_id = str(update.effective_user.id)
        user_data = load_user_data()
        
        if user_id not in user_data or not user_data[user_id]["inventory"]:
            await update.message.reply_text(
                "📭 Ваша коллекция пуста!\n"
                "Используйте /getcard чтобы получить первую карточку."
            )
            return
        
        inventory = user_data[user_id]["inventory"]
        total_points = user_data[user_id]["total_points"]
        
        # Статистика по редкостям
        rarity_count = {}
        for card in inventory:
            rarity = card["rarity"]
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
        
        stats_text = f"📊 **Коллекция пользователя** @{update.effective_user.username}:\n"
        stats_text += f"📚 Всего карточек: {len(inventory)}\n"
        stats_text += f"⭐ Всего очков: {total_points}\n\n"
        
        stats_text += "🎲 **По редкостям:**\n"
        for rarity, count in sorted(rarity_count.items(), 
                                  key=lambda x: list(RARITY_GROUPS.keys()).index(x[0])):
            emoji = RARITY_GROUPS[rarity]["emoji"]
            stats_text += f"{emoji} {rarity}: {count} шт.\n"
        
        # Последние 5 карточек
        stats_text += f"\n🆕 **Последние полученные:**\n"
        recent_cards = inventory[-5:][::-1]  # Последние 5 в обратном порядке
        for i, card in enumerate(recent_cards, 1):
            emoji = RARITY_GROUPS[card["rarity"]]["emoji"]
            stats_text += f"{i}. {emoji} {card['name']} ({card['points']} очков)\n"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в команде /inventory: {e}")
        await update.message.reply_text("❌ Произошла ошибка при просмотре коллекции")

def main():
    """Основная функция запуска бота"""
    # Проверка существования карточек
    missing_images = []
    for rarity, data in RARITY_GROUPS.items():
        for card in data["cards"]:
            if not os.path.exists(card['image']):
                missing_images.append(card['image'])
                logger.warning(f"Image not found: {card['image']}")
    
    if missing_images:
        logger.warning(f"Всего отсутствует {len(missing_images)} изображений")

    # Проверка суммы шансов
    total_chance = sum(data["chance"] for data in RARITY_GROUPS.values())
    if total_chance != 100:
        logger.warning(f"Total chance is {total_chance}% (should be 100%)")

    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавление обработчиков команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("getcard", get_card))
        application.add_handler(CommandHandler("inventory", show_inventory))
        application.add_handler(CommandHandler("rarities", show_rarities))
        
        logger.info("Бот запускается...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

if __name__ == "__main__":
    main()
