import os
from dotenv import load_dotenv
from supabase import create_client, Client


# load_environment_variables
load_dotenv()

# variables for Telegram connection
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# variables for Supabase connection
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
