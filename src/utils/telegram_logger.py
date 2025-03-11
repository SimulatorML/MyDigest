import requests
import logging
from datetime import datetime
from src.config import GROUP_LOGS_ID, TELEGRAM_BOT_TOKEN

class TelegramSender:
    def __init__(self, token = TELEGRAM_BOT_TOKEN):
        self.token = token
        self.url = f"https://api.telegram.org/bot{self.token}"

    # Функция для отправки сообщения с текстом text
    async def send_text(self, text: str, channel_id = GROUP_LOGS_ID):
        method = f"{self.url}/sendMessage"
        
        logging.info(f'Sending message to {channel_id}: {text}')
        
        text = text + "\n" + datetime.now().isoformat()

        r = requests.post(method, data={
            "chat_id": channel_id,
            "text": text
        })
        
        if r.status_code != 200:
            raise Exception(f"post_text error: {r.status_code}, {r.text}")