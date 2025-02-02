import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

TOKEN: str | None = os.getenv('TOKEN')
CHAT_ID: str | None = os.getenv('CHAT_ID')
STATE_FILE: Path = Path('state.json')
MESSAGES_DIR: Path = Path('messages_lists')

if not TOKEN or not CHAT_ID:
    raise ValueError("Необходимые переменные окружения (TOKEN или CHAT_ID) не заданы!")
