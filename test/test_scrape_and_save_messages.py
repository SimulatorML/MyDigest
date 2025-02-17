import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from src.scraper import TelegramScraper
from src.data.database import SupabaseDB, supabase

scraper = TelegramScraper()
db = SupabaseDB(supabase)

async def test_scrape_and_save_messages():
    user_id = 11  # Замените на реальный user_id
    channel_name = "@channel_example"  # Замените на реальный канал
    channel_id = 1  # Замените на реальный channel_id

    # Подключаемся к клиенту Telegram
    await scraper.connect_client()

    # Скрапим сообщения
    messages = await scraper.scrape_messages(channel_name, limit=100, time_range="24h")
    if not messages:
        print(f"Нет сообщений для канала {channel_name}.")
        return

    # Сохраняем сообщения в БД
    for msg in messages:
        success = await db.save_channel_news(channel_id, msg["message"], msg["message_date"].isoformat())
        if success:
            print(f"Сообщение {msg['message_id']} успешно сохранено.")
        else:
            print(f"Ошибка при сохранении сообщения {msg['message_id']}.")

    # Закрываем соединение с Telegram API
    if scraper.client.is_connected():
        await scraper.client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_scrape_and_save_messages())