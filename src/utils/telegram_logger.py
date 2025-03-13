import requests
import logging
from datetime import datetime
from src.config import GROUP_LOGS_ID, TELEGRAM_BOT_TOKEN, TURN_TG_LOGGER, TITLE_TG_LOGGER


class TelegramSender:
    def __init__(self, token=TELEGRAM_BOT_TOKEN, turn=TURN_TG_LOGGER, title=TITLE_TG_LOGGER):
        self.token = token
        self.url = f"https://api.telegram.org/bot{self.token}"
        self.turn = turn
        self.title = title  # Заголовок для сообщений

    async def send_text(self, text: str, channel_id=GROUP_LOGS_ID):
        if not self.turn:
            return
        
        # Если логгер включен, то
        method = f"{self.url}/sendMessage"
        logging.info(f'Sending message to {channel_id}: {text}')
        
        # Формируем текст: заголовок + текст + дата
        full_text = (
            f"{self.title}\n"  # Заголовок для сообщений, например, Testing
            f"{text}\n\n"      # Основной текст
            f"{datetime.now()}"  # Время отправки
        )
        
        r = requests.post(method, data={
            "chat_id": channel_id,
            "text": full_text
        })
        
        if r.status_code != 200:
            raise Exception(f"post_text error: {r.status_code}, {r.text}")

# Глобальный экземпляр с настройками по умолчанию
telegram_sender = TelegramSender()