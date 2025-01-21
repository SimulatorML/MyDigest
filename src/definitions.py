import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()
DATA_DIR = ROOT_DIR / "data"
CHANNELS_FILE = DATA_DIR / "channels.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")