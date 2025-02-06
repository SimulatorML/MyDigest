from typing import List, Dict, Any
from src.data.database import fetch_user_channels, fetch_user


class DatabaseManager:
    def __init__(self, supabase_client):
        self.client = supabase_client

    async def get_user_channels(self, user_id: int) -> List[str]:
        """Get channels for specific user"""
        channels = await fetch_user_channels(user_id)
        return [channel["channel_name"] for channel in channels] if channels else []

    async def get_user_digest_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user's digest preferences"""
        user = await fetch_user(user_id)
        return user.get("digest_settings", {})
