import logging
import json
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio
import random
from datetime import time, timezone, timedelta
from telegram.error import TelegramError
from telegram import Update
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()
# Настройка токена и ID чата
TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
    
# Устанавливаем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Файлы для хранения данных
MENTION_MESSAGES_FILE = 'mention_messages.json'
STATE_FILE = 'state.json'

# Загрузка сообщений из файла или установка по умолчанию
try:
    with open(MENTION_MESSAGES_FILE, 'r') as file:
        MENTION_MESSAGES = json.load(file)
except FileNotFoundError:
    MENTION_MESSAGES = [
        "Сегодня обсуждаем {name}! 💏 Кажется что его недавно заметили с девушкой! Он нарушает законы гомесексуального подполья! Возможно стоит поддержать его и удержать от падения в пропасть гетеросексуальных отношений!",
    ]

# Переменные для участников и очереди сообщений
participants = {}
shuffled_messages = []
last_chosen_member_id = None

# Загрузка состояния из файла
def load_state():
    global participants, shuffled_messages, last_chosen_member_id
    try:
        with open(STATE_FILE, 'r') as file:
            state = json.load(file)
            participants = state.get("participants", {})
            shuffled_messages = state.get("shuffled_messages", [])
            last_chosen_member_id = state.get("last_chosen_member_id", None)
            logger.info("Состояние успешно загружено.")
    except FileNotFoundError:
        logger.warning("Файл состояния не найден. Используются значения по умолчанию.")

# Сохранение состояния в файл
def save_state():
    state = {
        "participants": participants,
        "shuffled_messages": shuffled_messages,
        "last_chosen_member_id": last_chosen_member_id
    }
    with open(STATE_FILE, 'w') as file:
        json.dump(state, file)
    logger.info("Состояние успешно сохранено.")

# Получение следующего уникального сообщения
def get_next_message():
    global shuffled_messages

    # Если очередь сообщений пуста, перезаполняем и перетасовываем
    if not shuffled_messages:
        shuffled_messages = MENTION_MESSAGES[:]
        random.shuffle(shuffled_messages)

    # Берем следующее сообщение
    message = shuffled_messages.pop()
    save_state()  # Сохраняем состояние
    return message

async def track_participants(update: Update, context):
    """Сохранение участников, отправляющих сообщения."""
    if update.message and update.message.from_user:
        user = update.message.from_user
        if user.id not in participants:
            participants[user.id] = user.mention_html()
            save_state()  # Сохраняем состояние при добавлении участника
            logger.info(f"Добавлен участник: {user.full_name} ({user.id})")
    else:
        logger.warning("Получено обновление без сообщения от пользователя.")

async def send_daily_message(context):
    """Ежедневное сообщение с упоминанием случайного участника."""
    global last_chosen_member_id
    try:
        logger.info("Выполняется отправка ежедневного сообщения.")
        members = [{"id": user_id, "mention_html": mention_html} for user_id, mention_html in participants.items()]

        if members:
            # Исключаем последнего выбранного участника
            available_members = [member for member in members if member["id"] != last_chosen_member_id]

            if not available_members:
                available_members = members  # Если все уже были выбраны, сбрасываем ограничения

            chosen_member = random.choice(available_members)
            last_chosen_member_id = chosen_member["id"]  # Запоминаем выбранного участника
            save_state()  # Сохраняем состояние

            # Получаем уникальное сообщение
            message = get_next_message().format(name=chosen_member["mention_html"])
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode='HTML'
            )
            logger.info("Сообщение успешно отправлено.")
        else:
            logger.warning("Не удалось найти участников чата.")
    except TelegramError as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")

async def remind(update, context):
    """Команда /remind для отправки сообщения вручную."""
    global last_chosen_member_id
    logger.info("Получена команда /remind")
    try:
        members = [{"id": user_id, "mention_html": mention_html} for user_id, mention_html in participants.items()]

        if members:
            # Исключаем последнего выбранного участника
            available_members = [member for member in members if member["id"] != last_chosen_member_id]

            if not available_members:
                available_members = members  # Если все уже были выбраны, сбрасываем ограничения

            chosen_member = random.choice(available_members)
            last_chosen_member_id = chosen_member["id"]  # Запоминаем выбранного участника
            save_state()  # Сохраняем состояние

            # Получаем уникальное сообщение
            message = get_next_message().format(name=chosen_member["mention_html"])
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode='HTML'
            )
            await update.message.reply_text("Напоминание успешно отправлено!")
            logger.info("Напоминание отправлено через команду /remind.")
        else:
            await update.message.reply_text("Не удалось найти участников чата.")
            logger.warning("Не удалось найти участников чата.")
    except TelegramError as e:
        logger.error(f"Ошибка при выполнении команды /remind: {e}")
        await update.message.reply_text("Произошла ошибка при отправке напоминания.")

async def start(update: Update, context):
    """Ответ на команду /start"""
    logger.info("Получена команда /start")
    await update.message.reply_text('Бот запущен! Я буду собирать участников и упоминать их.')

async def get_chat_id(update, context):
    """Ответ на команду /chatid"""
    logger.info("Получена команда /chatid")
    await update.message.reply_text(f"Chat ID: {update.message.chat_id}")

async def list_participants(update: Update, context):
    """Команда /participants для вывода списка участников."""
    if participants:
        participants_list = "\n".join([f"{mention_html}" for mention_html in participants.values()])
        await update.message.reply_text(f"Список участников:\n{participants_list}", parse_mode='HTML')
    else:
        await update.message.reply_text("Список участников пока пуст.")

async def add_message(update: Update, context):
    """Команда /addmessage для добавления нового сообщения в MENTION_MESSAGES."""
    if context.args:
        new_message = " ".join(context.args)
        MENTION_MESSAGES.append(new_message)
        with open(MENTION_MESSAGES_FILE, 'w') as file:
            json.dump(MENTION_MESSAGES, file)
        await update.message.reply_text("Сообщение добавлено в список упоминаний.")
        logger.info(f"Добавлено новое сообщение: {new_message}")
    else:
        await update.message.reply_text("Пожалуйста, введите сообщение после команды /addmessage.")

async def remove_message(update: Update, context):
    """Команда /removemessage для удаления сообщения из MENTION_MESSAGES по индексу."""
    if context.args and context.args[0].isdigit():
        index = int(context.args[0])
        if 0 <= index < len(MENTION_MESSAGES):
            removed_message = MENTION_MESSAGES.pop(index)
            with open(MENTION_MESSAGES_FILE, 'w') as file:
                json.dump(MENTION_MESSAGES, file)
            await update.message.reply_text(f"Сообщение удалено: {removed_message}")
            logger.info(f"Удалено сообщение: {removed_message}")
        else:
            await update.message.reply_text("Неверный индекс. Пожалуйста, укажите корректный индекс сообщения.")
    else:
        await update.message.reply_text("Пожалуйста, укажите индекс сообщения после команды /removemessage.")

async def list_messages(update: Update, context):
    """Команда /listmessages для вывода всех сообщений в MENTION_MESSAGES."""
    if MENTION_MESSAGES:
        messages_list = "\n".join([f"{idx}: {msg}" for idx, msg in enumerate(MENTION_MESSAGES)])
        await update.message.reply_text(f"Список сообщений:\n{messages_list}")
    else:
        await update.message.reply_text("Список сообщений пуст.")

async def main():
    """Главная функция запуска приложения."""
    # Загружаем состояние при старте
    load_state()

    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Убедитесь, что JobQueue запускается автоматически
    job_queue = application.job_queue
    if job_queue is None:
        raise RuntimeError("JobQueue не инициализирован. Убедитесь, что PTB установлен с поддержкой JobQueue.")

    # Устанавливаем ежедневное задание
    local_tz = timezone(timedelta(hours=6))  # Астана (UTC+6)
    job_time = time(10, 0, 0, tzinfo=local_tz)
    job_queue.run_daily(
        send_daily_message,
        time=job_time,
        days=(0, 1, 2, 3, 4, 5, 6)  # Каждый день недели
    )

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chatid", get_chat_id))
    application.add_handler(CommandHandler("remind", remind))
    application.add_handler(CommandHandler("participants", list_participants))
    application.add_handler(CommandHandler("addmessage", add_message))
    application.add_handler(CommandHandler("removemessage", remove_message))
    application.add_handler(CommandHandler("listmessages", list_messages))

    # Отслеживание сообщений для добавления участников
    application.add_handler(MessageHandler(filters.ALL, track_participants))

    # Запуск бота
    await application.run_polling()


if __name__ == '__main__':
    import nest_asyncio

    # Применяем патч для вложенных event loops
    nest_asyncio.apply()

    # Запускаем main в существующем loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
