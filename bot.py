import os
import json
import random
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация - получаем токен из переменных окружения Railway
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8295319122:AAFGvZ1GFqPv8EkCTQnXjSKzd4dOG8rz1bg')
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

# Загрузка данных пользователей
def load_user_data():
    try:
        with open('user_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info("user_data.json не найден, создаю новый файл")
        return {}

def save_user_data(data):
    with open('user_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Получение случайной карточки
def get_random_card():
    roll = random.random() * 100
    current = 0
    
    selected_rarity = None
    for rarity, data in RARITY_GROUPS.items():
        current += data["chance"]
        if roll <= current:
            selected_rarity = rarity
            break
    
    if selected_rarity is None:
        selected_rarity = list(RARITY_GROUPS.keys())[0]
    
    cards_in_rarity = RARITY_GROUPS[selected_rarity]["cards"]
    card = random.choice(cards_in_rarity)
    
    card["rarity"] = selected_rarity
    card["emoji"] = RARITY_GROUPS[selected_rarity]["emoji"]
    card["rarity_chance"] = RARITY_GROUPS[selected_rarity]["chance"]
    
    return card

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# Команда /rarities
async def show_rarities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rarity_info = "🎲 **Шансы редкостей:**\n"
    for rarity, data in RARITY_GROUPS.items():
        emoji = data["emoji"]
        chance = data["chance"]
        card_count = len(data["cards"])
        rarity_info += f"{emoji} {rarity}: {chance}% ({card_count} карточек)\n"
    
    await update.message.reply_text(rarity_info, parse_mode='Markdown')

# Команда /getcard
async def get_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = load_user_data()

    last_used = user_data.get(user_id, {}).get('last_used')
    if last_used:
        last_time = datetime.fromisoformat(last_used)
        time_diff = datetime.now() - last_time
        
        # Правильный расчет оставшегося времени
        if time_diff < timedelta(minutes=COOLDOWN_MINUTES):
            remaining_seconds = (timedelta(minutes=COOLDOWN_MINUTES) - time_diff).total_seconds()
            minutes = int(remaining_seconds // 60)
            seconds = int(remaining_seconds % 60)
            
            await update.message.reply_text(
                f"⏳ Следующая карточка будет доступна через {minutes} минут {seconds} секунд"
            )
            return

    card = get_random_card()
    
    caption = (
        f"🎴 **Вы получили карточку:** {card['name']}\n"
        f"{card['emoji']} **Редкость:** {card['rarity']}\n"
        f"⭐ **Очки:** {card['points']}\n"
        f"🎲 Шанс редкости: {card['rarity_chance']}%"
    )

    try:
        with open(card['image'], 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=caption, parse_mode='Markdown')
    except FileNotFoundError:
        await update.message.reply_text(f"❌ Ошибка: изображение {card['image']} не найдено")

    if user_id not in user_data:
        user_data[user_id] = {"inventory": [], "total_points": 0}
    
    user_data[user_id]["inventory"].append({
        "card_id": card["id"],
        "name": card["name"],
        "rarity": card["rarity"],
        "points": card["points"],
        "acquired": datetime.now().isoformat()
    })
    
    user_data[user_id]["total_points"] += card["points"]
    user_data[user_id]['last_used'] = datetime.now().isoformat()
    save_user_data(user_data)
    
    logger.info(f"User {user_id} received card: {card['name']}")

# Команда /inventory
async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data or not user_data[user_id]["inventory"]:
        await update.message.reply_text("📭 Ваша коллекция пуста!\nИспользуйте /getcard чтобы получить первую карточку.")
        return
    
    inventory = user_data[user_id]["inventory"]
    total_points = user_data[user_id]["total_points"]
    
    rarity_count = {}
    for card in inventory:
        rarity = card["rarity"]
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    
    stats_text = f"📊 **Ваша коллекция:**\n"
    stats_text += f"📚 Всего карточек: {len(inventory)}\n"
    stats_text += f"⭐ Всего очков: {total_points}\n\n"
    
    stats_text += "🎲 **По редкостям:**\n"
    for rarity, count in rarity_count.items():
        emoji = RARITY_GROUPS[rarity]["emoji"]
        stats_text += f"{emoji} {rarity}: {count} шт.\n"
    
    stats_text += f"\n🆕 **Последние полученные:**\n"
    recent_cards = inventory[-5:]
    for card in recent_cards:
        emoji = RARITY_GROUPS[card["rarity"]]["emoji"]
        stats_text += f"{emoji} {card['name']} ({card['points']} очков)\n"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

if __name__ == "__main__":
    # Проверка существования карточек
    for rarity, data in RARITY_GROUPS.items():
        for card in data["cards"]:
            if not os.path.exists(card['image']):
                logger.warning(f"Image not found: {card['image']}")
    
    # Проверка суммы шансов
    total_chance = sum(data["chance"] for data in RARITY_GROUPS.values())
    if total_chance != 100:
        logger.warning(f"Total chance is {total_chance}% (should be 100%)")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getcard", get_card))
    application.add_handler(CommandHandler("inventory", show_inventory))
    application.add_handler(CommandHandler("rarities", show_rarities))
    
    logger.info("Бот запущен на Railway...")
    application.run_polling()
