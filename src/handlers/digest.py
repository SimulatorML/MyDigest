from aiogram import Router, types, Bot
from aiogram.filters import Command
from collections import defaultdict
from src.scraper import TelegramScraper
from src.summarization import summarize

router = Router()
scraper = TelegramScraper()

@router.message(Command("start"))
async def start_handler(msg: types.Message):
    await msg.answer(
        "Hello! It's MyDigest bot. I can help you collect personal news sources and provide daily digests.",
        reply_markup=types.ReplyKeyboardRemove()
    )


@router.message(Command("daily_digest"))
async def daily_digest(msg: types.Message) -> None:
    user_id = msg.from_user.id
    messages = await scraper.get_user_digest(user_id, time_range="24h")

    if not messages:
        await msg.answer("No new messages in the last 24 hours.")
        return

    # Группируем сообщения по каналам
    messages_by_channel = defaultdict(list)
    for message in messages:
        messages_by_channel[message["channel"]].append(message)

    # Создаем и отправляем дайджест для каждого канала
    for channel, channel_messages in messages_by_channel.items():
        summary = summarize(channel_messages, channel)
        await msg.answer(f"📢 Дайджест для {channel}: \n\n{summary}")

