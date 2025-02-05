from datetime import datetime
from src.scraper import scrape_messages
from src.summarization import summarize
from src.data.database import save_user_digest
from src.data.database_manager import DatabaseManager
from src.data.database import supabase


async def create_and_save_digest(user_id: int):
    db_manager = DatabaseManager(supabase)
    user_channels = await db_manager.get_user_channels(
        user_id)

    for channel in user_channels:
        messages = await scrape_messages(
            channel["channel_name"], limit=5, time_range="24h")  # scrape 5 messages from each channel over the last 24 hours
        if messages:
            digest_content = summarize(
                messages, channel["channel_name"])  # summarize the messages, return list
            creation_timestamp = datetime.now().isoformat()
            await save_user_digest(
                user_id, channel["channel_id"], digest_content, creation_timestamp)  # save the digest to the database
