import random
import logging
from datetime import datetime, timedelta
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from state_manager import StateManager
from message_manager import MessageManager
from config import CHAT_ID

logger = logging.getLogger(__name__)

# Список забавных сообщений от уставшего бота
TIRED_BOT_MESSAGES = [
    "🍺 Бот устал и ушёл в бар обсуждать ваши переписки с другими ботами.\n\n"
    "🗣️ \"Этот парень снова пишет post... Как же он меня достал!\"\n"
    "⌛ Бот протрезвеет через {time}. Надеемся. 😵‍💫",

    "⚠️ Бот ушёл спать... но перед этим он сохранил все ваши запросы и лайки. 📂\n"
    "👀 В этот момент он подбирает подходящую рекламу для вас и пишет отчёт вашему работодателю.\n\n"
    "⌛ Бот вернётся через {time}, но вы ему не рады. 🤭",

    "🤖 Бот временно недоступен. Он ушёл рассказывать своему психологу о том, что вы слишком часто вы вызываете `post_gachi`. Это его беспокоит\n"
    "⌛ Вернётся через {time}. Успейте удалить компромат! 🏃‍♂️💨",

    "📡 Бот ушёл проверять, сколько раз вы искали \"странные вещи\" в Google.\n"
    "⌛ Бот снова в строю через {time}. Надеемся, вы тоже. 🤯",

    "🛠️ Бот перезагружается... Тем временем он отправил вашу историю браузера вашему лучшему другу.\n"
    "😏 Не благодарите. Мы всегда готовы помочь.\n\n"
    "⌛ Бот вернётся через {time}. А вот ваша репутация — уже нет. 😂",

    "🔄 Бот на техобслуживании. Он обновляет систему...\n"
    "...а также ищет ваши старые комментарии в интернете, чтобы напомнить вам, каким кринжовым вы были в 2013 году. 🫣\n\n"
    "⌛ Вернётся через {time}, но теперь он знает о вас всё. 👁️",
]

# Параметры ограничения: 30 минут между отправками
RATE_LIMIT = timedelta(minutes=30)
last_message_time: Optional[datetime] = None  # время последней отправки сообщения


async def track_new_users(update: Update, state_manager: StateManager) -> None:
    """
    Отслеживает новые сообщения и добавляет пользователей в список участников,
    если их еще нет в state.json.
    """
    user = update.message.from_user
    user_id = str(user.id)
    user_name = f'<a href="tg://user?id={user_id}">{user.first_name}</a>'

    # Логируем ID и имя пользователя
    logger.info(f"Сообщение от {user_id} ({user.first_name})")

    # Проверяем, есть ли пользователь в списке участников
    if user_id not in state_manager.participants:
        state_manager.participants[user_id] = user_name
        await state_manager.save_state()  # Сохраняем обновленный список участников
        logger.info(f"Добавлен новый участник: {user_name}")

def get_rate_limit_remaining() -> Optional[timedelta]:
    """
    Возвращает оставшееся время до возможности отправки следующего сообщения,
    или None, если ограничение снято.
    """
    global last_message_time
    now = datetime.now()
    if last_message_time is None or now - last_message_time >= RATE_LIMIT:
        return None
    else:
        return RATE_LIMIT - (now - last_message_time)

def update_last_message_time() -> None:
    """
    Обновляет время последней отправки на текущее.
    """
    global last_message_time
    last_message_time = datetime.now()

async def post_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       state_manager: StateManager, message_manager: MessageManager,
                       category: str) -> None:
    """
    Отправляет сообщение в чат, подставляя имя участника в шаблон.
    
    Логика:
    - Для выбранной категории проверяем, есть ли перемешанный список сообщений.
    - Если список пуст, создаём его с помощью random.sample из оригинального списка.
    - Извлекаем первое сообщение (pop(0)), подставляем имя участника и отправляем.
    - Состояние (очередь сообщений) сохраняется после отправки.
    """
    try:
        participant, participant_id = state_manager.get_random_participant()
        if not participant:
            await update.message.reply_text("Нет доступных участников!")
            return

        # Получаем очередь сообщений для выбранной категории
        message_list = state_manager.shuffled_messages.get(category, [])
        if not message_list:
            original_messages = message_manager.categories.get(category, [])
            if not original_messages:
                await update.message.reply_text(f"Нет сообщений в категории '{category}'!")
                return
            state_manager.shuffled_messages[category] = random.sample(original_messages, len(original_messages))
            message_list = state_manager.shuffled_messages[category]

        message = message_list.pop(0).replace("{name}", participant)
        await state_manager.save_state()
        await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
    except Exception as e:
        logger.exception(f"Ошибка при отправке сообщения в категории '{category}': {e}")
        await update.message.reply_text("Произошла ошибка при отправке сообщения. Попробуйте позже.")

async def post_any(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   state_manager: StateManager, message_manager: MessageManager) -> None:
    """
    Отправляет случайное сообщение из случайной категории.
    """
    try:
        if not message_manager.categories:
            await update.message.reply_text("Нет доступных категорий!")
            return
        category = random.choice(list(message_manager.categories.keys()))
        await post_message(update, context, state_manager, message_manager, category)
    except Exception as e:
        logger.exception(f"Ошибка при отправке случайного сообщения: {e}")
        await update.message.reply_text("Произошла ошибка при отправке сообщения. Попробуйте позже.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       message_manager: MessageManager) -> None:
    """
    Отправляет список доступных команд.
    """
    try:
        commands = "/post - Отправить случайное сообщение\n"
        for category in message_manager.categories:
            commands += f"/post_{category} - Отправить сообщение из категории '{category}'\n"
        commands += "/help - Показать список доступных команд"
        await update.message.reply_text(commands)
    except Exception as e:
        logger.exception(f"Ошибка при обработке команды help: {e}")
        await update.message.reply_text("Произошла ошибка при обработке команды help.")

def make_post_handler(category: str, state_manager: StateManager,
                      message_manager: MessageManager):
    """
    Фабрика обработчиков команд для отправки сообщений из указанной категории.
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await post_message(update, context, state_manager, message_manager, category)
    return handler

async def post_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               state_manager: StateManager, message_manager: MessageManager) -> None:
    """
    Единый обработчик для команд /post и /post_<category>.
    Если команда ровно /post, вызывается post_any (случайная категория).
    Если команда имеет вид /post_<category>, отправляется сообщение из указанной категории.
    
    Перед выполнением команды проверяется ограничение: сообщение может быть отправлено не чаще, чем раз в 1 минуту.
    Если ограничение не позволяет, отправляется сообщение о том, что бот устал, с указанием оставшегося времени.
    """
    try:
        raw_command = update.message.text.strip().split()[0].lstrip('/')
        command = raw_command.split('@')[0]  # Удаляем упоминание бота, если есть

        # Логируем полученную команду
        logger.info(f"Получена команда: {command}")

        # Проверяем ограничение по времени
        remaining = get_rate_limit_remaining()
        if remaining is not None:
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            time_left = f"{minutes} минут {seconds} секунд" if minutes else f"{seconds} секунд"

            logger.info(f"Команда отклонена. Осталось {minutes} мин {seconds} сек до следующей отправки.")

            tired_message = random.choice(TIRED_BOT_MESSAGES).format(time=time_left)

            await update.message.reply_text(tired_message)
  
            return

        # Если ограничение прошло, обновляем время последней отправки
        update_last_message_time()

        # Логируем загруженные категории
        logger.info(f"Доступные категории: {list(message_manager.categories.keys())}")

        if command == "post":
            logger.info("Отправка случайного сообщения из любой категории.")
            await post_any(update, context, state_manager, message_manager)
        elif command.startswith("post_"):
            category = command.replace("post_", "").lower()  # Приводим к нижнему регистру

            # Логируем выбранную категорию
            logger.info(f"Выбранная категория: {category}")

            if category in message_manager.categories:
                logger.info(f"Категория '{category}' найдена. Отправка сообщения...")
                await post_message(update, context, state_manager, message_manager, category)
            else:
                logger.warning(f"Категория '{category}' не найдена!")
                await update.message.reply_text(f"Категория '{category}' не найдена.")
        else:
            logger.warning(f"Неизвестная команда: {command}")
            await update.message.reply_text("Неизвестная команда.")
    except Exception as e:
        logger.exception(f"Ошибка в post_command_handler: {e}")
        await update.message.reply_text("Произошла ошибка при обработке команды.")


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Глобальный обработчик необработанных исключений.
    """
    logger.exception("Необработанное исключение:", exc_info=context.error)
    if update and hasattr(update, "message") and update.message:
        try:
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        except Exception as e:
            logger.exception("Ошибка при отправке сообщения об ошибке:", exc_info=e)

