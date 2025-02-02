import random
import logging
from pathlib import Path
from typing import Dict, List
from json_utils import load_json_file

logger = logging.getLogger(__name__)

class MessageManager:
    """
    Класс для загрузки и хранения сообщений по категориям.
    """
    def __init__(self, messages_dir: Path, categories: Dict[str, List[str]]) -> None:
        self.messages_dir = messages_dir
        self.categories = categories

    @classmethod
    async def create(cls, messages_dir: Path) -> "MessageManager":
        """
        Фабричный метод для асинхронного создания экземпляра MessageManager,
        загружая все файлы вида messages_*.json из указанной директории.
        """
        categories: Dict[str, List[str]] = {}
        for file in messages_dir.glob("messages_*.json"):
            if file.is_file():
                category = file.stem.replace("messages_", "")
                messages = await load_json_file(file, default=[])
                # Если сообщения присутствуют, перемешиваем их
                if messages:
                    messages = random.sample(messages, len(messages))
                categories[category] = messages
        return cls(messages_dir, categories)
