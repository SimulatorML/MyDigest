# scraping.py
import asyncio
import os
import json
from telethon import TelegramClient, errors
from datetime import datetime, timedelta
from config import api_id, api_hash, phone_number

# Initialize Telethon client
client = TelegramClient("parsing_2.session", api_id, api_hash)

# Connect to Telegram client
async def connect_client():
    """Ensure the Telethon client is connected."""
    if not client.is_connected():
        await client.start(phone=phone_number)
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
async def scrape_messages(entity_name, limit=400, time_range="24h"):
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
