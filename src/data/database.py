# import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from supabase import create_client, Client
from supabase import AuthApiError, PostgrestAPIError
from src.config.config import SUPABASE_URL, SUPABASE_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class SupabaseErrorHandler:
    @staticmethod
    def handle_error(e: Exception, user_id: None, channel_id: None) -> None:
        error_map = {
            AuthApiError: ("AuthError", 500),
            PostgrestAPIError: ("ApiError", 400),
            ConnectionError: ("ConnectionError", 503),
        }
        msg = f"{error_map.get(type(e))[0]} у пользователя {user_id}: {str(e)}" if user_id else f"{error_map.get(type(e))[0]} у канала {channel_id}: {str(e)}"
        print(msg)  # В будущем заменить на логирование


class SupabaseDB:
    def __init__(self, supabase_client):
        self.client = supabase_client

    async def fetch_user(self, user_id: int) -> int:
        """
        Retrieve user ID from the database.

        :param user_id: The ID of the user to retrieve.
        :return: The ID of the user if found, otherwise None.
        :raises: SupabaseErrorHandler if an error occurs.
        """
        try:
            response = (
                self.client.table("users")
                .select("user_id")
                .eq("user_id", user_id)
                .execute()
            )
            return response.data[0]["user_id"] if response.data else None
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def add_user(
        self, user_id: int, username: str, login_timestamp: str = None
    ) -> Dict[str, Any]:
        """
        Add or update a user in the database.

        :param user_id: The ID of the user to add or update.
        :param username: The username of the user to add or update.
        :param login_timestamp: The timestamp of the user's last login.
                                 Defaults to the current time if not provided.
        :return: The response data from the database operation.
        :raises: SupabaseErrorHandler if an error occurs.
        """
        try:
            response = (
                self.client.table("users")
                .upsert(
                    {
                        "user_id": user_id,
                        "username": username,
                        "login_timestamp": login_timestamp,
                    }
                )
                .execute()
            )
            if response.data:
                print("Пользователь успешно добавлен или обновлен.")
            else:
                print(f"Ошибка при добавлении пользователя: {response.data}")
            return response.data
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def fetch_user_channels(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve the channels associated with a given user from the database.

        :param user_id: The ID of the user whose channels are to be retrieved.
        :return: A list of dictionaries containing the user's channels.
                 Each dictionary contains the keys "user_id", "channel_name", and "addition_timestamp".
        :raises: SupabaseErrorHandler if an error occurs.
        """
        try:
            response = (
                self.client.table("user_channels")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def add_user_channels(
        self, user_id: int, channels: List[str], addition_timestamp: str = None
    ) -> bool:
        """
        Add specified channels to a given user in the database.

        :param user_id: The ID of the user whose channels are to be added.
        :param channels: A set of channel names to add.
        :param addition_timestamp: The timestamp of the user's action.
                                    Defaults to the current time if not provided.
        :return: True if the operation was successful, otherwise handles exceptions.
        """
        try:
            data = [
                {
                    "user_id": user_id,
                    "channel_name": channel if channel.startswith("@") else None,
                    "channel_link": f"https://t.me/{channel[1:]}",
                    "addition_timestamp": addition_timestamp,
                }
                for channel in channels
            ]

            response = self.client.table("user_channels").upsert(data).execute()

            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def delete_user_channels(self, user_id: int, channels: List[str]) -> bool:
        """
        Delete specified channels from a given user in the database.

        :param user_id: The ID of the user whose channels are to be deleted.
        :param channels: A set of channel names to delete.
        :return: True if the operation was successful, otherwise handles exceptions.
        """
        try:
            for channel in channels:
                self.client.table("user_channels").delete().eq("user_id", user_id).eq(
                    "channel_name", channel
                ).execute()
            return True
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def clear_user_channels(self, user_id: int) -> bool:
        """
        Clear all channels associated with a given user from the database.

        :param user_id: The ID of the user whose channels are to be cleared.
        :return: The response data from the database operation.
        """
        try:
            self.client.table("user_channels").delete().eq("user_id", user_id).execute()
            return True
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def save_channel_news(
        self, channel_id: int, news: str, addition_timestamp: str
    ) -> bool:
        """
        Save a news piece from a given channel in the database.

        :param channel_id: The ID of the channel the news was retrieved from.
        :param news: The news piece as a string.
        :param addition_timestamp: The timestamp of the news addition.
        :return: True if the operation was successful, otherwise handles exceptions.
        """
        try:
            response = (
                self.client.table("channel_news")
                .upsert(
                    {
                        "channel_id": channel_id,
                        "news": news,
                        "addition_timestamp": addition_timestamp,
                    }
                )
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, None, channel_id)
            return False

    async def cleanup_old_news(self):
        """
        Cleanup old news pieces from the database.
        
        This method deletes all news pieces older than 1 day from the database.
        """
        try:
            cutoff_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
            self.client.table("channels_news").delete().lt(
                "addition_timestamp", cutoff_time
            ).execute()
        except Exception as e:
            print(f"Ошибка при очистке старых новостей: {e}")

    async def save_user_digest(
        self,
        user_id: int,
        channel_id: int,
        digest_content: str,
        creation_timestamp: str,
    ) -> bool:
        """
        Save a user's digest to the database.

        :param user_id: The ID of the user the digest belongs to.
        :param channel_id: The ID of the channel the digest was generated from.
        :param digest_content: The content of the digest as a string.
        :param creation_timestamp: The timestamp of the digest creation.
        :return: True if the operation was successful, otherwise handles exceptions.
        """
        try:
            response = (
                self.client.table("digests")
                .upsert(
                    {
                        "user_id": user_id,
                        "channel_id": channel_id,
                        "digest_content": digest_content,
                        "creation_timestamp": creation_timestamp,
                    }
                )
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, channel_id)
            return False
