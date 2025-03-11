import os
from dotenv import load_dotenv
from src.utils.telegram_logger import TelegramLogHandler

# Load environment variables
load_dotenv()

# Variables
NEWS_CHECK_INTERVAL = 600  # интервал скрапинга в секундах

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE_NUMBER = os.getenv('TELEGRAM_PHONE_NUMBER')

# Group for logs
GROUP_LOGS_ID = os.getenv('GROUP_LOGS_ID')

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# LLM configuration
MISTRAL_KEY = os.getenv('MISTRAL_KEY')


## Глобальные экземпляры

# Логгера
telegram_logger = TelegramLogHandler(TELEGRAM_BOT_TOKEN, GROUP_LOGS_ID)