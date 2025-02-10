import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from telethon import TelegramClient, errors
from typing import List, Dict, Any
from src.data.database import supabase
from src.data.database_manager import DatabaseManager
from src.config.config import *
from src.summarization import summarize


class TelegramScraper:
    def __init__(self):
        """
        Initializes the TelegramScraper class by setting up the Telegram client, database manager,
        and message threshold for sending digests.
        """

        self.client = TelegramClient("parsing_2.session", API_ID, API_HASH)
        self.db_manager = DatabaseManager(supabase)
        self.threshold_messages = 2

    async def connect_client(self):
        """
        Ensures that the Telethon client is connected.
        If the client is not connected, it starts the client using the provided phone number.
        """

        if not self.client.is_connected():
            await self.client.start(phone=PHONE_NUMBER)
            print("Telethon client connected")

    async def get_entity(self, entity_name):
        """
        Fetches a Telegram entity (such as a channel or user) by its name.

        Args:
            entity_name (str): The username or channel name of the Telegram entity.

        Returns:
            dict or None: A dictionary representing the entity object if retrieval
            is successful, otherwise None if the entity is not found or an error occurs.
        """
        try:
            if not self.client.is_connected():
                print("Telethon client disconnected. Reconnecting...")
                await self.connect_client()

            entity = await self.client.get_entity(entity_name)
            print(f"Accessing {entity_name}")
            return entity
        except Exception as e:
            print(f"Failed to access {entity_name}: {e}")
            return None

    async def scrape_messages(self, entity_name: str, limit: int = 400, time_range: str = "24h") -> List[Dict[str, Any]]:
        """
        Scrapes messages from a given Telegram channel within a specified time range.

        Args:
            entity_name (str): The username or channel name of the Telegram entity.
            limit (int, optional): The maximum number of messages to scrape. Defaults to 400.
            time_range (str, optional): The time range for filtering messages.
                                        Accepts "24h" for the last 24 hours or "7d" for the last 7 days.
                                        Defaults to "24h".

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary contains:
                - 'message_id' (int): The unique ID of the message.
                - 'message' (str): The text content of the message.
                - 'message_date' (datetime): The timestamp of when the message was sent.
            Returns an empty list if no messages are found or an error occurs.
        """
        entity = await self.get_entity(entity_name)
        if not entity:
            return []

        now = datetime.utcnow()
        start_time = now - timedelta(hours=24) if time_range == "24h" else now - timedelta(days=7)

        messages = []
        try:
            async for message in self.client.iter_messages(entity, limit=limit):
                message_date_naive = message.date.replace(tzinfo=None)
                if message_date_naive >= start_time:
                    messages.append({
                        "message_id": message.id,
                        "message": message.text,
                        "message_date": message.date
                    })
                else:
                    break
        except errors.FloodWaitError as e:
            print(f'Have to sleep {e.seconds} seconds')
            await asyncio.sleep(e.seconds)
            return await self.scrape_messages(entity_name, limit, time_range)
        except Exception as e:
            print(f"Failed to scrape messages: {e}")

        return messages

    async def get_user_digest(self, user_id: int, time_range: str = "24h") -> List[Dict[str, Any]]:
        """
        Retrieves a digest of messages from the Telegram channels that a user is subscribed to.

        Args:
            user_id (int): The unique identifier of the Telegram user.
            time_range (str, optional): The time range for filtering messages.
                                        Accepts "24h" for the last 24 hours or "7d" for the last 7 days.
                                        Defaults to "24h".

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary contains:
                - 'message_id' (int): The unique ID of the message.
                - 'message' (str): The text content of the message.
                - 'message_date' (datetime): The timestamp of when the message was sent.
                - 'channel' (str): The name of the channel the message belongs to.
            Returns an empty list if the user is not subscribed to any channels or no messages are found.
        """
        user_channels = await self.db_manager.get_user_channels(user_id)

        if not user_channels:
            return []

        all_messages = []
        for channel in user_channels:
            messages = await self.scrape_messages(channel, time_range=time_range)
            for msg in messages:
                msg["channel"] = channel
            all_messages.extend(messages)

        return all_messages

    async def check_new_messages(self, user_id: int, time_range: str = "1h"):
        """Проверяет новые сообщения и отправляет дайджест пользователю."""
        try:
            user_channels = await self.db_manager.get_user_channels(user_id)

            if not user_channels:
                await bot.send_message(user_id, "Пожалуйста, добавьте каналы. Чтобы добавить канал, вызовите /add_channels")
                await asyncio.sleep(600)
                continue

            #setting one hour to run the parser
            for channel in user_channels:
                now = datetime.utcnow()
                one_hour_ago = now - timedelta(hours=1)

                if channel in sent_digest_channels:
                    continue

                messages = await self.scrape_messages(channel, limit=100)
                if not messages:
                    continue

                recent_messages = [
                    msg for msg in messages if msg["message_date"].replace(tzinfo=None) >= one_hour_ago
                ]

                if len(recent_messages) >= self.threshold_messages:
                    summary = summarize(recent_messages, channel)
                    await bot.send_message(user_id, f"📢 Дайджест за последний час для {channel}:\n\n{summary}")

        except Exception as e:
            logging.error(f"Ошибка в check_new_messages: {e}")
            await self.bot.send_message(user_id, "❌ Ошибка при получении дайджеста. Попробуйте позже.")

    async def start_auto_news_check(self, user_id: int, interval: int = 1800):
        """Фоновая проверка сообщений для конкретного пользователя каждые N секунд."""
        print(f"🔍 Запускаю фоновую проверку для пользователя {user_id} (интервал {interval // 60} мин)...")

        while user_id in self.running_tasks:
            print(f"🔄 Проверка новых сообщений для {user_id}...")
            await self.check_new_messages(user_id, time_range="1h")
            print(f"✅ Проверка завершена. Следующая через {interval // 60} минут.")
            await asyncio.sleep(interval)  # Ждем перед следующей проверкой

    def stop_auto_news_check(self, user_id: int):
        """Останавливает фоновую проверку новостей для пользователя."""
        if user_id in self.running_tasks:
            self.running_tasks[user_id].cancel()
            del self.running_tasks[user_id]
            return True
        return False