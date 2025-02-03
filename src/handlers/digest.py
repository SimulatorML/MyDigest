from typing import List, Dict, Any
from aiogram import Router, types, Bot
from aiogram.filters import Command

from src.data.database_manager import DatabaseManager
from src.scraper import connect_client, scrape_messages, get_user_digest
from src.summarization import summarize

router = Router()
CHANNEL_NAME = "rbc_news"

@router.message(Command("start"))
async def start_handler(msg: types.Message):
    await msg.answer(
        "Hello! It's MyDigest bot. I can help you collect personal news sources and provide daily digests.",
        reply_markup=types.ReplyKeyboardRemove()
    )

@router.message(Command("help"))
async def send_menu(msg: types.Message):
    await msg.answer(
        "Command /daily_digest gives you the daily digest of news.\n"
        "Command /weekly_digest gives you the weekly digest of news."
    )

@router.message(Command("daily_digest"))
async def daily_digest(msg: types.Message) -> None:
    user_id = msg.from_user.id
    messages = await get_user_digest(user_id, time_range="24h")

    if not messages:
        await msg.answer("No new messages in the last 24 hours.")
        return

    # Группируем сообщения по каналам
    messages_by_channel = defaultdict(list)
    print(messages_by_channel)
    for message in messages:
        messages_by_channel[message["channel"]].append(message)

    # Создаем и отправляем дайджест для каждого канала
    for channel, channel_messages in messages_by_channel.items():
        summary = summarize(channel_messages, channel)
        await msg.answer(f"📢 Дайджест для {channel}: \n\n{summary}")

@router.message(Command("weekly_digest"))
async def weekly_digest(msg: types.Message):
    await connect_client()
    messages = await scrape_messages(entity_name=CHANNEL_NAME, limit=24, time_range="7d")
    if messages:
        summary = summarize(messages, CHANNEL_NAME)
        await msg.answer(f"Недельный дайджест новостей:\n\n{summary}")
    else:
        await msg.answer("No messages found for the weekly digest.")
