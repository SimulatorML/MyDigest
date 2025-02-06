import asyncio
from telethon import TelegramClient, errors
from datetime import datetime, timedelta
from src.config.config import API_ID, API_HASH, PHONE_NUMBER
from typing import List, Dict, Any
# from src.data.database_manager import DatabaseManager
# from src.data.database import save_digest_to_db
# from src.config.config import supabase
# from src.summarization import summarize

# Initialize Telethon client
client = TelegramClient("parsing_2.session", API_ID, API_HASH)


# Connect to Telegram client
async def connect_client():
    """Ensure the Telethon client is connected."""
    if not client.is_connected():
        await client.start(phone=PHONE_NUMBER)
        print("Telethon client connected")


# Get entity by name
async def get_entity(entity_name):
    try:
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


# async def get_user_digest(user_id: int, time_range: str = "24h") -> List[Dict[str, Any]]:
#     """Get digest for specific user based on their channels"""
#     db_manager = DatabaseManager(supabase)
#     user_channels = await db_manager.get_user_channels(user_id)
    
#     all_messages = []
#     for channel in user_channels:
#         messages = await scrape_messages(channel, time_range=time_range)
#         all_messages.extend(messages)
    
#     return all_messages


# async def create_and_save_digest(user_id: int):
#     """Create a digest for a user and save it to the database."""
#     db_manager = DatabaseManager(supabase)
#     user_channels = await db_manager.get_user_channels(user_id)  # return list of channels for user
    
#     for channel in user_channels:
#         messages = await scrape_messages(channel, limit=5, time_range="24h")
#         if messages:
#             creation_timestamp = datetime.now().isoformat()
#             digest_content = summarize(messages, channel)
#             success = await save_digest_to_db(user_id, channel, digest_content, creation_timestamp)
#             if not success:
#                 print(f"Failed to save digest for user {user_id} and channel {channel}")
