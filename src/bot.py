import logging
import asyncio
from ssl import CHANNEL_BINDING_TYPES
import json

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from charset_normalizer import from_path

from config import bot_token
from src.scraper import connect_client, scrape_messages
from summarization import summarize



# Initialize bot and dispatcher
bot = Bot(token=bot_token)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
CHANNEL_NAME = "rbc_news"

# Command Handlers
@router.message(Command("start"))
async def start_handler(msg: types.Message):
    await msg.answer("Hello! It's MyDigest bot. I can help you collect personal news sources and provide daily digests.",
                     reply_markup=types.ReplyKeyboardRemove())  # Remove the keyboard if any

@router.message(Command("help"))
async def send_menu(msg: types.Message):
    await msg.answer("Command /daily_digest gives you the daily digest of news.\n"
                     "Command /weekly_digest gives you the weekly digest of news.")

@router.message(Command("daily_digest"))
async def daily_digest(msg: types.Message):
    await connect_client()  # Ensure Telethon client is connected
    messages = await scrape_messages(entity_name=CHANNEL_NAME, limit=10, time_range="24h")
    if messages:
        summary = summarize(messages, CHANNEL_NAME)
        await msg.answer(f"Дневной дайджест новостей:\n\n{summary}")
    else:
        await msg.answer("No messages found for the daily digest.")

@router.message(Command("weekly_digest"))
async def weekly_digest(msg: types.Message):
    await connect_client()  # Ensure Telethon client is connected
    messages = await scrape_messages(entity_name=CHANNEL_NAME, limit=24, time_range="7d")
    if messages:
        #json_data = json.dumps(messages, indent=4, ensure_ascii=False)
        summary = summarize(messages, CHANNEL_NAME)
        await msg.answer(f"Недельный дайджест новостей:\n\n{summary}")
    else:
        await msg.answer("No messages found for the weekly digest.")



# Main function to start the bot
async def main():
    # Initialize the bot and connect to Telegram client
    await connect_client()

    # Register routers and start polling
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Run the bot
    asyncio.run(main())