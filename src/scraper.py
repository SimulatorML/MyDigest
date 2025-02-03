import asyncio
from telethon import TelegramClient, errors
from datetime import datetime, timedelta
from src.config.config import API_ID, API_HASH, PHONE_NUMBER
from typing import List, Dict, Any
from src.data.database_manager import DatabaseManager
from src.config.config import supabase

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

        entity = await client.get_entity(entity_name)
        print(f"Accessing {entity_name}")
        return entity
    except Exception as e:
        print(f"Failed to access {entity_name}: {e}")
        return None

# Scrape messages from the channel
async def scrape_messages(entity_name: str, limit: int = 400, time_range: str = "24h") -> List[Dict[str, Any]]:
    """Scrapes messages from a Telegram channel.

    Args:
        entity_name (str): Name of the Telegram channel/entity
        limit (int, optional): Maximum number of messages to scrape. Defaults to 400.
        time_range (str, optional): Time range for messages ("24h" or "7d"). Defaults to "24h".

    Returns:
        List[Dict[str, Any]]: List of scraped messages with their metadata

    Raises:
        FloodWaitError: If Telegram enforces rate limiting
        Exception: For other unexpected errors
    """
    entity = await get_entity(entity_name)
    if not entity:
        return []

    now = datetime.now()
    if time_range == "24h":
        start_time = now - timedelta(hours=24)
    elif time_range == "7d":
        start_time = now - timedelta(days=7)
    else:
        print(f"Invalid time range: {time_range}")
        return []

    messages = []
    try:
        async for message in client.iter_messages(entity, limit=limit,):
            message_date_naive = message.date.replace(tzinfo=None)
            if message_date_naive >= start_time:
                messages.append({
                    "message_id": message.id,
                    "message": message.message
                })
            else:
                break
    except errors.FloodWaitError as e:
        print(f'Have to sleep {e.seconds} seconds')
        await asyncio.sleep(e.seconds)
        return await scrape_messages(entity_name, limit, time_range)
    except Exception as e:
        print(f"Failed to scrape messages: {e}")

    return messages

async def get_user_digest(user_id: int, time_range: str = "24h") -> List[Dict[str, Any]]:
    """Get digest for specific user based on their channels"""
    db_manager = DatabaseManager(supabase)
    user_channels = await db_manager.get_user_channels(user_id)

    if not user_channels:
        return []

        all_messages = []
        for channel in user_channels:
            messages = await self.scrape_messages(channel, time_range=time_range)
            for msg in messages:
                msg["channel"] = channel
            all_messages.extend(messages)

        return all_messages

    async def check_new_messages(self, user_id: int):
        """
        Background task that continuously checks for new messages in the channels a user is subscribed to.
        If the number of new messages in a channel within the last hour exceeds the threshold,
        a digest is generated and sent to the user.
        """
        sent_digest_channels = set()

        while True:
            user_channels = await self.db_manager.get_user_channels(user_id)

            if not user_channels:
                await asyncio.sleep(1800)
                continue

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

                    sent_digest_channels.add(channel)

            await asyncio.sleep(600)
            await asyncio.sleep(3600)
            sent_digest_channels.clear()
