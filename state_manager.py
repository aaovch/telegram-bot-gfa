import random
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from json_utils import load_json_file, save_json_file
from message_manager import MessageManager

logger = logging.getLogger(__name__)

class StateManager:
    """
    Класс для управления состоянием: участниками и очередями сообщений.
    """
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.participants: Dict[str, str] = {}           # {participant_id: participant_name}
        self.shuffled_messages: Dict[str, List[str]] = {}  # {category: [message1, message2, ...]}
        self.shuffled_participants: List[str] = []         # Список participant_id в случайном порядке

    async def load_state(self, message_manager: MessageManager) -> None:
        """
        Загружает состояние из файла и обновляет очереди сообщений, если это необходимо.
        """
        state: Dict[str, Any] = await load_json_file(self.state_file, default={})
        self.participants = state.get("participants", {})
        self.shuffled_messages = state.get("shuffled_messages", {})
        self.shuffled_participants = state.get("shuffled_participants", [])

        # Для каждой категории проверяем очередь сообщений
        for category, messages in message_manager.categories.items():
            if category not in self.shuffled_messages or not self.shuffled_messages[category]:
                if messages:
                    self.shuffled_messages[category] = random.sample(messages, len(messages))
                else:
                    self.shuffled_messages[category] = []

        if not self.shuffled_participants and self.participants:
            self.shuffled_participants = random.sample(list(self.participants.keys()), len(self.participants))

    async def save_state(self) -> None:
        """
        Сохраняет состояние в файл.
        """
        state = {
            "participants": self.participants,
            "shuffled_messages": self.shuffled_messages,
            "shuffled_participants": self.shuffled_participants
        }
        await save_json_file(self.state_file, state)

    def get_random_participant(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Выбирает участника без повторов, пока не пройдут все.
        Returns:
            Tuple[participant_name, participant_id]
        """
        if not self.shuffled_participants:
            if self.participants:
                self.shuffled_participants = random.sample(list(self.participants.keys()), len(self.participants))
            else:
                return None, None
        chosen_id = self.shuffled_participants.pop(0)
        return self.participants.get(chosen_id), chosen_id
