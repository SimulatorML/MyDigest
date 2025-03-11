import logging
import requests
from typing import Optional
from src.config.config import TELEGRAM_BOT_TOKEN, GROUP_LOGS_ID

class TelegramLogHandler(logging.Handler):
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = GROUP_LOGS_ID):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def send_message(self, text: str) -> Optional[requests.Response]:
        try:
            # Добавляем эмодзи в зависимости от уровня лога
            level_emoji = {
                logging.ERROR: "🔴",
                logging.WARNING: "⚠️",
                logging.INFO: "ℹ️",
                logging.DEBUG: "🔍"
            }.get(self.level, "📝")
            
            formatted_text = f"{level_emoji} {text}"
            
            # Разбиваем длинные сообщения на части
            max_length = 4000
            messages = [formatted_text[i:i+max_length] 
                      for i in range(0, len(formatted_text), max_length)]
            
            for msg in messages:
                response = requests.post(
                    self.base_url,
                    data={
                        "chat_id": self.chat_id,
                        "text": msg,
                        "parse_mode": "HTML"
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    print(f"Failed to send log to Telegram. Status code: {response.status_code}")
                    print(f"Error details: {response.text}")
                    print(f"Chat ID: {self.chat_id}")
                    return None
                
                return response
                
        except Exception as e:
            print(f"Error sending log to Telegram: {str(e)}")
            print(f"Chat ID: {self.chat_id}")
            return None

    def emit(self, record):
        try:
            msg = self.formatter.format(record)
            self.level = record.levelno
            self.send_message(msg)
        except Exception as e:
            print(f"Error in log handler: {e}")