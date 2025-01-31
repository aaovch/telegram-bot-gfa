import logging
import json
import os
import asyncio
import random
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути к файлам данных
STATE_FILE = 'state.json'
MESSAGES_DIR = '.'  # Директория с JSON-файлами категорий

# Функция загрузки JSON-файлов
def load_messages(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"Файл {filename} не найден или пуст. Используется пустой список.")
        return []

# Динамическое определение категорий
def load_categories():
    categories = {}
    for file in os.listdir(MESSAGES_DIR):
        if file.startswith("messages_") and file.endswith(".json"):
            category = file.replace("messages_", "").replace(".json", "")
            categories[category] = load_messages(file)
    return categories

# Загрузка сообщений
MESSAGES_CATEGORIES = load_categories()

# Глобальные переменные
participants = {}
shuffled_messages = {}
shuffled_participants = []

# Функции загрузки и сохранения данных
def load_json(filename, default):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"Файл {filename} не найден или пуст. Используется значение по умолчанию.")
        return default

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    logger.info(f"Данные сохранены в {filename}.")

def load_state():
    global participants, shuffled_messages, shuffled_participants
    state = load_json(STATE_FILE, {})
    participants = state.get("participants", {})

    # Загружаем состояния сообщений
    shuffled_messages = state.get("shuffled_messages", {})

    # Загружаем состояние участников
    shuffled_participants = state.get("shuffled_participants", [])

    # Проверяем, что все категории есть в shuffled_messages
    for category, messages in MESSAGES_CATEGORIES.items():
        if category not in shuffled_messages or not shuffled_messages[category]:
            shuffled_messages[category] = random.sample(messages, len(messages)) if messages else []

    # Если список участников пуст — перемешиваем заново
    if not shuffled_participants:
        shuffled_participants = random.sample(list(participants.keys()), len(participants)) if participants else []

def save_state():
    state = {
        "participants": participants,
        "shuffled_messages": shuffled_messages,
        "shuffled_participants": shuffled_participants
    }
    save_json(STATE_FILE, state)

def get_random_participant():
    """Выбирает участника без повторов, пока не пройдут все."""
    global shuffled_participants
    if not shuffled_participants:
        if participants:
            shuffled_participants = random.sample(list(participants.keys()), len(participants))
        else:
            return None, None

    chosen_id = shuffled_participants.pop(0)  # Берем первого и удаляем
    return participants[chosen_id], chosen_id

async def post_message(update: Update, context, category):
    """Отправка сообщения в чат со случайным участником."""
    participant, chosen_id = get_random_participant()
    if not participant:
        await update.message.reply_text("Нет доступных участников!")
        return
    
    # Получаем список сообщений категории
    message_list = shuffled_messages.get(category, [])
    
    # Если список пуст, перемешиваем заново
    if not message_list:
        original_messages = MESSAGES_CATEGORIES.get(category, [])
        if not original_messages:
            await update.message.reply_text(f"Нет сообщений в категории '{category}'!")
            return
        shuffled_messages[category] = random.sample(original_messages, len(original_messages))
        message_list = shuffled_messages[category]

    # Берем первое сообщение и удаляем его из списка
    message = message_list.pop(0).replace("{name}", participant)
    
    # Сохраняем состояние
    save_state()

    # Отправляем сообщение
    await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')

async def post_any(update: Update, context):
    """Отправка случайного сообщения из случайной категории."""
    if not MESSAGES_CATEGORIES:
        await update.message.reply_text("Нет доступных категорий!")
        return
    category = random.choice(list(MESSAGES_CATEGORIES.keys()))
    await post_message(update, context, category)

async def help_command(update: Update, context):
    commands = "/post - Отправить случайное сообщение\n"
    for category in MESSAGES_CATEGORIES:
        commands += f"/post_{category} - Отправить сообщение из категории '{category}'\n"
    commands += "/help - Показать список доступных команд"
    await update.message.reply_text(commands)

async def main():
    load_state()
    application = Application.builder().token(TOKEN).build()

    # Автоматическое добавление хендлеров
    for category in MESSAGES_CATEGORIES:
        application.add_handler(CommandHandler(f"post_{category}", lambda update, context, cat=category: post_message(update, context, cat)))

    application.add_handler(CommandHandler("post", post_any))
    application.add_handler(CommandHandler("help", help_command))
    
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
