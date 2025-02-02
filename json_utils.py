import json
import logging
from pathlib import Path
from typing import Any
import aiofiles

logger = logging.getLogger(__name__)

async def load_json_file(file_path: Path, default: Any) -> Any:
    """
    Асинхронно загружает JSON-данные из файла.
    
    Если файла не существует, создаёт его с содержимым default и возвращает default.
    Если файл существует, но имеет неверный формат, возвращает default.
    
    Args:
        file_path: Путь к JSON-файлу.
        default: Значение по умолчанию, которое будет возвращено и записано в файл, если его нет.
        
    Returns:
        Загруженные данные или значение по умолчанию.
    """
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            contents = await f.read()
            return json.loads(contents)
    except FileNotFoundError:
        logger.warning(f"Файл {file_path} не найден. Создаем файл с дефолтным значением.")
        await save_json_file(file_path, default)
        return default
    except json.JSONDecodeError as e:
        logger.warning(f"Файл {file_path} имеет неверный формат: {e}. Используется значение по умолчанию.")
        return default

async def save_json_file(file_path: Path, data: Any) -> None:
    """
    Асинхронно сохраняет данные в формате JSON в файл.
    
    Args:
        file_path: Путь к файлу, в который необходимо сохранить данные.
        data: Данные для сохранения.
    """
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            text = json.dumps(data, indent=4, ensure_ascii=False)
            await f.write(text)
        logger.info(f"Данные успешно сохранены в {file_path}.")
    except Exception as e:
        logger.exception(f"Ошибка при сохранении данных в {file_path}: {e}")
