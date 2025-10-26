import os
import json
import random
import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

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
    "Редкая": {
        "chance": 30,
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
        "chance": 23,
        "emoji": "🔵",
        "cards": [
            {"id": 3, "name": "Ярик", "image": "cards/SuperRare/card3.jpg", "points": 200},
            {"id": 3.1, "name": "УВЗ", "image": "cards/SuperRare/card3.1.jpg", "points": 200},
            {"id": 3.2, "name": "Чижик", "image": "cards/SuperRare/card3.2.jpg", "points": 200},
            {"id": 3.3, "name": "Фикс в Прайме", "image": "cards/SuperRare/card3.3.jpg", "points": 200},
            {"id": 3.4, "name": "Гоша", "image": "cards/SuperRare/card3.4.jpg", "points": 200},
            {"id": 3.5, "name": "Оператор у зеркала", "image": "cards/SuperRare/card3.5.jpg", "points": 200},
            {"id": 3.6, "name": "Молочная кремка", "image": "cards/SuperRare/card3.6.jpg", "points": 200},
            {"id": 3.7, "name": "Клубничная кремка", "image": "cards/SuperRare/card3.7.jpg", "points": 200},
        ]
    },
    "Эпическая": {
        "chance": 17,
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
        ]
    },
    "Мифическая": {
        "chance": 15,
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
        ]
    },
    "Легендарная": {
        "chance": 10,
        "emoji": "🟡",
        "cards": [
            {"id": 6, "name": "Стёпа с фанатами", "image": "cards/Legendary/card6.jpg", "points": 10000},
            {"id": 6.1, "name": "Тимофей и Ваня", "image": "cards/Legendary/card6.1.jpg", "points": 10000},
            {"id": 6.2, "name": "Михаил Мевдедь после сорев", "image": "cards/Legendary/card6.2.jpg", "points": 10000},
            {"id": 6.3, "name": "Оператор с цветочком", "image": "cards/Legendary/card6.3.jpg", "points": 10000},
            {"id": 6.4, "name": "Бульба Мен", "image": "cards/Legendary/card6.4.jpg", "points": 10000},
            {"id": 6.5, "name": "Белох", "image": "cards/Legendary/card6.5.jpg", "points": 10000},
            {"id": 6.6, "name": "Миша Combination", "image": "cards/Legendary/card6.6.jpg", "points": 10000},
            {"id": 6.7, "name": "Михаил Медвед на соревах", "image": "cards/Legendary/card6.7.jpg", "points": 10000},
        ]
    },
    "Секретная": {
        "chance": 4,
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
        ]
    },
    "Эксклюзивная": {
        "chance": 1,
        "emoji": "🟠",
        "cards": [
            {"id": 8, "name": "Миши в поезде", "image": "cards/Exclusive/card8.jpg", "points": 50000},
            {"id": 8.1, "name": "Миши в Туапсе", "image": "cards/Exclusive/card8.1.jpg", "points": 50000},
        ]
    },
}

# Промокоды
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
    }
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

# Загрузка данных промокодов
def load_promo_data():
    try:
        with open('promo_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info("promo_data.json не найден, создаю новый с начальными значениями")
        save_promo_data(PROMOCODES)
        return PROMOCODES.copy()

def save_promo_data(data):
    with open('promo_data.json', 'w', encoding='utf-8') as f:
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

# Получение карточки по ID
def get_card_by_id(card_id):
    for rarity_group in RARITY_GROUPS.values():
        for card in rarity_group["cards"]:
            if card["id"] == card_id:
                card["rarity"] = next(r for r, rg in RARITY_GROUPS.items() if card in rg["cards"])
                card["emoji"] = RARITY_GROUPS[card["rarity"]]["emoji"]
                return card
    return None

# Получение случайной карточки определенной редкости
def get_random_card_by_rarity(target_rarity):
    if target_rarity not in RARITY_GROUPS:
        return None
    
    cards_in_rarity = RARITY_GROUPS[target_rarity]["cards"]
    card = random.choice(cards_in_rarity)
    
    card["rarity"] = target_rarity
    card["emoji"] = RARITY_GROUPS[target_rarity]["emoji"]
    card["rarity_chance"] = RARITY_GROUPS[target_rarity]["chance"]
    
    return card

# Добавление карточки пользователю
def add_card_to_user(user_id, card):
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {"inventory": [], "total_points": 0, "used_promocodes": []}
    
    user_data[user_id]["inventory"].append({
        "card_id": card["id"],
        "name": card["name"],
        "rarity": card["rarity"],
        "points": card["points"],
        "acquired": datetime.now(timezone.utc).isoformat(),
        "from_promo": True  # Помечаем что карта из промокода
    })
    
    user_data[user_id]["total_points"] += card["points"]
    save_user_data(user_data)
    
    logger.info(f"User {user_id} received card from promo: {card['name']}")

# Получение статистики по карточкам пользователя
def get_user_card_stats(user_id):
    user_data = load_user_data()
    if user_id not in user_data:
        return {}
    
    inventory = user_data[user_id]["inventory"]
    card_stats = {}
    
    for card in inventory:
        card_id = card["card_id"]
        if card_id not in card_stats:
            # Находим оригинальную карточку для получения изображения и других данных
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
        "/rarities - Информация о редкостях\n"
        "/promo <код> - Активировать промокод\n\n"
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
        # Преобразуем строку времени в объект datetime с учетом временной зоны
        if last_used.endswith('Z'):
            last_time = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
        else:
            last_time = datetime.fromisoformat(last_used)
        
        # Получаем текущее время с временной зоной
        current_time = datetime.now(timezone.utc)
        
        # Если last_time наивный (без временной зоны), считаем его UTC
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        
        # Вычисляем разницу во времени
        time_passed = current_time - last_time
        cooldown_duration = timedelta(minutes=COOLDOWN_MINUTES)
        
        # Проверяем, прошел ли кулдаун
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
        user_data[user_id] = {"inventory": [], "total_points": 0, "used_promocodes": []}
    
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
    
    logger.info(f"User {user_id} received card: {card['name']}")

# Команда /inventory - показывает меню выбора редкости
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
    for rarity in RARITY_GROUPS:
        if rarity in rarity_count and rarity_count[rarity] > 0:
            emoji = RARITY_GROUPS[rarity]["emoji"]
            count = rarity_count[rarity]
            keyboard.append([InlineKeyboardButton(f"{emoji} {rarity} ({count})", callback_data=f"rarity_{rarity}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    stats_text = (
        f"📊 **Ваша коллекция:**\n"
        f"📚 Всего карточек: {len(inventory)}\n"
        f"⭐ Всего очков: {total_points}\n\n"
        f"🎲 **Выберите редкость для просмотра:**"
    )
    
    await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

# Обработчик выбора редкости
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
    context.user_data["rarity_cards"] = list(rarity_cards.items())  # Список (card_id, stats)
    context.user_data["current_card_index"] = 0
    
    # Показываем первую карточку
    await show_card_navigation(query, context)

# Функция для показа карточки с навигацией
async def show_card_navigation(query, context):
    user_data = context.user_data
    rarity = user_data["current_rarity"]
    cards = user_data["rarity_cards"]
    current_index = user_data["current_card_index"]
    
    if current_index >= len(cards):
        current_index = 0
        user_data["current_card_index"] = 0
    
    card_id, card_stats = cards[current_index]
    
    # Создаем подпись
    caption = (
        f"🎴 **{card_stats['name']}**\n"
        f"{card_stats['emoji']} **Редкость:** {card_stats['rarity']}\n"
        f"📦 **Количество:** {card_stats['count']} шт.\n"
        f"⭐ **Очки за штуку:** {card_stats['points']}\n"
        f"💰 **Всего очков:** {card_stats['total_points']}\n"
        f"📄 **Карточка {current_index + 1} из {len(cards)}**"
    )
    
    # Создаем клавиатуру навигации
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if len(cards) > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="nav_prev"))
        nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{len(cards)}", callback_data="nav_info"))
        nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data="nav_next"))
        keyboard.append(nav_buttons)
    
    # Кнопка возврата к выбору редкости
    keyboard.append([InlineKeyboardButton("🔙 Назад к редкостям", callback_data="back_to_rarities")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        with open(card_stats['image'], 'rb') as photo:
            if query.message.photo:
                # Если сообщение уже содержит фото, редактируем его
                await query.message.edit_media(
                    media=InputMediaPhoto(photo, caption=caption, parse_mode='Markdown'),
                    reply_markup=reply_markup
                )
            else:
                # Если нет фото, отправляем новое сообщение
                await query.message.reply_photo(
                    photo=photo,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
    except FileNotFoundError:
        # Если изображение не найдено, отправляем текстовое сообщение
        await query.edit_message_text(
            f"❌ Изображение карточки не найдено!\n\n{caption}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Обработчик навигации
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
        await show_inventory_from_callback(query, context)
        return
    
    await show_card_navigation(query, context)

# Возврат к выбору редкости из callback
async def show_inventory_from_callback(query, context):
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data or not user_data[user_id]["inventory"]:
        await query.edit_message_text("📭 Ваша коллекция пуста!\nИспользуйте /getcard чтобы получить первую карточку.")
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
    for rarity in RARITY_GROUPS:
        if rarity in rarity_count and rarity_count[rarity] > 0:
            emoji = RARITY_GROUPS[rarity]["emoji"]
            count = rarity_count[rarity]
            keyboard.append([InlineKeyboardButton(f"{emoji} {rarity} ({count})", callback_data=f"rarity_{rarity}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    stats_text = (
        f"📊 **Ваша коллекция:**\n"
        f"📚 Всего карточек: {len(inventory)}\n"
        f"⭐ Всего очков: {total_points}\n\n"
        f"🎲 **Выберите редкость для просмотра:**"
    )
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

# Команда /promo
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
    
    # Инициализация данных пользователя если нужно
    if user_id not in user_data:
        user_data[user_id] = {"inventory": [], "total_points": 0, "used_promocodes": []}
    
    # Проверка использованных промокодов
    if "used_promocodes" not in user_data[user_id]:
        user_data[user_id]["used_promocodes"] = []
    
    # Проверяем использовал ли пользователь уже этот промокод
    if promo_code in user_data[user_id]["used_promocodes"]:
        await update.message.reply_text("❌ Вы уже использовали этот промокод!")
        return
    
    # Проверка существования промокода
    if promo_code not in promo_data:
        await update.message.reply_text("❌ Неверный промокод!")
        return
    
    promo = promo_data[promo_code]
    
    # Проверка оставшихся использований
    if promo["uses_left"] <= 0:
        await update.message.reply_text("❌ Промокод больше не действителен!")
        return
    
    # Обработка промокода
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
    else:
        await update.message.reply_text("❌ Неизвестный тип промокода!")
        return
    
    # Отправка карточки
    caption = (
        f"🎁 **Вы активировали промокод!**\n"
        f"🎴 **Получена карточка:** {card['name']}\n"
        f"{card['emoji']} **Редкость:** {card['rarity']}\n"
        f"⭐ **Очки:** {card['points']}\n"
        f"🎟️ Промокод: {promo_code}"
    )
    
    try:
        with open(card['image'], 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=caption, parse_mode='Markdown')
    except FileNotFoundError:
        await update.message.reply_text(f"❌ Ошибка: изображение {card['image']} не найдено")
        return
    
    # Обновление данных
    promo_data[promo_code]["uses_left"] -= 1
    save_promo_data(promo_data)
    
    user_data[user_id]["used_promocodes"].append(promo_code)
    add_card_to_user(user_id, card)
    
    # Информация об остатке использований
    uses_left = promo_data[promo_code]["uses_left"]
    if uses_left > 0:
        uses_info = f"Осталось использований: {uses_left}/{promo['max_uses']}"
    else:
        uses_info = "Промокод полностью использован!"
    
    await update.message.reply_text(f"✅ Промокод успешно активирован!\n{uses_info}")

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

    # Загрузка данных промокодов при старте
    load_promo_data()

    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getcard", get_card))
    application.add_handler(CommandHandler("inventory", show_inventory))
    application.add_handler(CommandHandler("rarities", show_rarities))
    application.add_handler(CommandHandler("promo", use_promo))
    
    # Обработчики callback-ов для инвентаря
    application.add_handler(CallbackQueryHandler(show_rarity_cards, pattern="^rarity_"))
    application.add_handler(CallbackQueryHandler(handle_navigation, pattern="^nav_"))
    application.add_handler(CallbackQueryHandler(show_inventory_from_callback, pattern="^back_to_rarities$"))
    
    logger.info("Бот запущен на Railway...")
    application.run_polling()
