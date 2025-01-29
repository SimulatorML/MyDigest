import pathlib
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Telegram API creds
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()
DATA_DIR = ROOT_DIR / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"
