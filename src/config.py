import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Telegram API creds
api_id = os.getenv('TELEGRAM_API_ID')
api_hash = os.getenv('TELEGRAM_API_HASH')
phone_number = os.getenv('TELEGRAM_PHONE_NUMBER')
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')


print(f"API ID: {api_id}, API Hash: {api_hash}, Phone: {phone_number}, Bot Token: {bot_token}")
