import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# onboarding video ids
ONBOARDING_VIDEO_ID = "BAACAgIAAxkDAAIU6GgMrgKVaHT_X6iYy1vixh3EZ25bAAL_bAACmoRoSBaF67Kr0zMcNgQ"  # видео с шагами
# ONBOARDING_VIDEO_ID = "BAACAgIAAxkDAAIVvWgM67y8KpMYK5kFyv79ixzaCiQ7AAJycQACmoRoSIZQeTItoKRNNgQ"  # видео без шагов !!!

# Деактивация юзеров, если они используют бота
DEACTIVATE_USER = os.getenv("DEACTIVATE_USER", "False").lower() in ("true", "1")

# Interval Variables
NEWS_CHECK_INTERVAL = 3600  # интервал скрапинга в секундах
DAY_RANGE_INTERVAL = 7     # интервал скрепинга в днях для определения темы канала

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
