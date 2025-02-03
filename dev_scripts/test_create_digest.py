import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from src.data.database import fetch_user_channels, save_user_digest
from src.scraper import scrape_messages, connect_client
from src.summarization import summarize
from src.scraper import client


async def create_and_save_digest(user_id: int):
    """
    Create and save a digest for the specified user.

    This function connects to the Telegram client and retrieves the list of channels for the given user.
    It then scrapes messages from each channel over the last 7 days, generates a digest summary,
    and saves the digest to the database. If no channels or messages are found, it logs appropriate messages.

    Args:
        user_id (int): The ID of the user for whom to create and save the digest.

    Returns:
        None
    """

    # Подключаемся к клиенту Telegram
    await connect_client()

    # Получаем каналы пользователя
    channels = await fetch_user_channels(
        user_id
    )  # Return dict of channel_id and channel_name

    if not channels:
        print("Нет каналов для пользователя.")
        return

    for channel in channels:
        # Получаем сообщения из канала
        messages = await scrape_messages(
            channel["channel_name"], limit=5, time_range="7d"
        )
        if not messages:
            print(f"Нет сообщений для канала {channel['channel_name']}.")
            continue

        # Создаём дайджест
        digest_content = summarize(messages, channel["channel_name"])
        creation_timestamp = datetime.now().isoformat()

        # Сохраняем дайджест в БД
        success = await save_user_digest(
            user_id, channel["channel_id"], digest_content, creation_timestamp
        )
        if success:
            print(f"Дайджест для канала {channel['channel_name']} успешно сохранён.")
        else:
            print(
                f"Ошибка при сохранении дайджеста для канала {channel['channel_name']}."
            )


async def main():
    user_id = 1  # Замените на реальный user_id
    try:
        await create_and_save_digest(user_id)
    finally:
        # Даем время на завершение фоновых задач - тогда не возникает RuntimeWarning
        await asyncio.sleep(1)
        # Закрываем соединение с Telegram API
        if client.is_connected():
            await client.disconnect()
            print("Соединение с Telegram API закрыто")


if __name__ == "__main__":
    asyncio.run(main())
