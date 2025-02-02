import asyncio
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
import nest_asyncio

from config import TOKEN, STATE_FILE, MESSAGES_DIR
from message_manager import MessageManager
from state_manager import StateManager
from handlers import help_command, post_command_handler, global_error_handler, track_new_users
from telegram import Update
from telegram.ext import MessageHandler, filters


def setup_logging() -> None:
    """
    Настраивает логирование с использованием RotatingFileHandler для файла и консольного вывода.
    """
    from logging.handlers import RotatingFileHandler
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=2, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

async def main() -> None:
    """
    Основная асинхронная функция для запуска Telegram-бота.
    
    Создает менеджеры сообщений и состояния, регистрирует обработчики:
    - Единый обработчик для команды /post (а также для /post_<category>) с ограничением: можно отправлять только одно сообщение в 30 минут.
    - Обработчик для команды /help без ограничений.
    - Глобальный обработчик ошибок.
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск бота")
    
    # Создаем менеджеры сообщений и состояния
    message_manager = await MessageManager.create(MESSAGES_DIR)
    state_manager = StateManager(STATE_FILE)
    await state_manager.load_state(message_manager)
    
    # Создаем приложение Telegram-бота
    application = Application.builder().token(TOKEN).build()
    
    # Единый обработчик для всех команд, связанных с отправкой сообщений (/post и /post_<category>)
    async def post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await post_command_handler(update, context, state_manager, message_manager)
    
    # Обработчик для команды /help
    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await help_command(update, context, message_manager)
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("post", post_handler))
    for category in message_manager.categories.keys():
        application.add_handler(CommandHandler(f"post_{category}", post_handler))
    application.add_handler(CommandHandler("help", help_handler))
    
    # Регистрируем глобальный обработчик ошибок
    application.add_error_handler(global_error_handler)

    async def message_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await track_new_users(update, state_manager)

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_tracker))
    
    await application.run_polling()

if __name__ == "__main__":
    # nest_asyncio используется для совместимости в некоторых окружениях (например, Jupyter)
    nest_asyncio.apply()
    asyncio.run(main())
