import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from supabase import create_client, Client
from supabase import AuthApiError, PostgrestAPIError
from src.config.config import SUPABASE_URL, SUPABASE_KEY
import hashlib
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
        logging.error(msg)  # В будущем заменить на логирование


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
                logging.info("Пользователь успешно добавлен или обновлен.")
            else:
                logging.info("Ошибка при добавлении пользователя: %s", response.data)
            return response.data
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def set_user_receiving_news(self, user_id: int, is_receiving: bool) -> bool:
        """
        Set bool for users who are receiving news
        :param user_id:
        :param is_receiving:
        :return:
        """
        try:
            response = (
                self.client.table("users")
                .update({"is_receiving_news": is_receiving})
                .eq("user_id", user_id)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)
            return False

    async def retrieve_current_users(self) -> List[Dict[str, Any]]:
        """
        Retrieve users who are receiving news
        :param self
        :return:
        """
        try:
            response = (
                self.client.table("users")
                .select("user_id")
                .eq("is_receiving_news", True)
                .execute()
            )
            return response
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, None, None)

    async def fetch_user_channels(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve the channels associated with a given user from the database.

        :param user_id: The ID of the user whose channels are to be retrieved.
        :return: A list of dictionaries containing the user's channels.
                 Each dictionary contains the keys "channel_name" and "channel_id".
        :raises: SupabaseErrorHandler if an error occurs.
        """
        try:
            response = (
                self.client.table("user_channels")
                .select("channel_id")
                .eq("user_id", user_id)
                .eq("is_active", True)  # Берем только активные каналы
                .execute()
            )
            channel_ids = [channel["channel_id"] for channel in response.data]
            channels = []
            for channel_id in channel_ids:
                channel_name = await self.fetch_channel_name(channel_id)
                if channel_name:
                    channels.append({"channel_name": channel_name, "channel_id": channel_id})
            return channels
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def add_channels(self, channels: List[str], channel_topics: List[str], addition_timestamp: str = None) -> bool:
        """
        Add multiple channels to the database.

        :param channels: A list of channel names to add.
        :param channel_topics: A list of channel topics corresponding to the channels.
        :param addition_timestamp: The timestamp when the channels were added. Defaults to None.
        :return: True if the channels were successfully added, False otherwise.
        :raises: Logs an error if an exception occurs during the database operation.
        """

        try:
            values = []
            for channel in channels:
                channel_id = await self.generate_channel_hash(channel)
                channel_topic = channel_topics[channels.index(channel)] if channel_topics else None
                channel_link = f"https://t.me/{channel[1:]}"

                values.append({
                    "channel_id": channel_id,
                    "channel_name": channel,
                    "channel_topic": channel_topic,
                    "channel_link": channel_link,
                    "addition_timestamp": addition_timestamp
                })

            response = self.client.table("channels").insert(values).execute()
            return bool(response.data)
        except Exception as e:
            logging.error("Error during adding channels %s : %s", channels, e)
            return False

    async def add_single_channel(self, channel_name: str, channel_topic: str, addition_timestamp: str = None) -> bool:
        """
        Add a single channel to the database.

        :param channel_name: The name of the channel to add.
        :param channel_topic: The topic of the channel.
        :param addition_timestamp: The timestamp when the channel was added. Defaults to None.
        :return: True if the channel was successfully added, False otherwise.
        """
        try:
            channel_id = await self.generate_channel_hash(channel_name)
            channel_link = f"https://t.me/{channel_name[1:]}"

            data = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "channel_topic": channel_topic,
                "channel_link": channel_link,
                "addition_timestamp": addition_timestamp
            }

            response = self.client.table("channels").insert(data).execute()
            return bool(response.data)
        except Exception as e:
            logging.error("Error during adding single channel %s : %s", channel_name, e)
            return False

    async def link_user_channels(self, user_id: int, channel_ids: List[int], addition_timestamp: str = None) -> bool:
        """
        Link a user to multiple channels in the database.

        :param user_id: The ID of the user to link.
        :param channel_ids: A list of channel IDs to link the user to.
        :param addition_timestamp: The timestamp when the user was linked to the channels. Defaults to None.
        :return: True if the user was successfully linked to all channels, False otherwise.
        """

        try:
            values = [
                {
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "addition_timestamp": addition_timestamp,
                    "is_active": True
                }
                for channel_id in channel_ids
            ]

            response = self.client.table("user_channels").insert(values).execute()
            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)
            return False

    async def link_user_single_channel(self, user_id: int, channel_id: int, addition_timestamp: str = None) -> bool:
        """
        Link a user to a single channel in the database.

        :param user_id: The ID of the user to link.
        :param channel_id: The ID of the channel to link.
        :param addition_timestamp: The timestamp when the user was linked to the channel.
        :return: True if the user was successfully linked to the channel, False otherwise.
        """
        try:
            response = self.client.table("user_channels").upsert(
                {
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "addition_timestamp": addition_timestamp,
                    "is_active": True
                },
                on_conflict="user_id,channel_id"  # Указываем уникальные поля для конфликта
            ).execute()

            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)
            return False

    async def delete_user_channels(self, user_id: int, channels: List[str]) -> bool:
        """
        Delete specified channels from a given user in the database.

        :param user_id: The ID of the user whose channels are to be deleted.
        :param channels: A list of channel names to delete.
        :return: True if the operation was successful, otherwise handles exceptions.
        """
        try:
            channel_ids = [await self.fetch_channel_id(channel) for channel in channels if await self.fetch_channel_id(channel)]
            if not channel_ids:
                return False

            response = self.client.table("user_channels").update(
                {"is_active": False}
            ).eq("user_id", user_id).in_("channel_id", channel_ids).execute()

            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)
            return False

    async def clear_user_channels(self, user_id: int) -> bool:
        """
        Clear all channels associated with a given user from the database.

        :param user_id: The ID of the user whose channels are to be cleared.
        :return: The response data from the database operation.
        """
        try:
            response = self.client.table("user_channels").update(
                {"is_active": False}
            ).eq("user_id", user_id).execute()

            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)
            return False

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
                self.client.table("channels_news")
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
            logging.error("Ошибка при очистке старых новостей: %s", e)

    async def save_user_digest(
        self,
        user_id: int,
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
                        "digest_content": digest_content,
                        "creation_timestamp": creation_timestamp,
                    }
                )
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)
            return False

    async def fetch_channel_id(self, channel_name: str) -> int:
        """
        Ensure that a channel with the given name exists in the database.

        :param channel_name: The name of the channel to check.
        :return: The ID of the channel if it exists, False otherwise.
        """
        try:
            response = self.client.table("channels").select("*").eq("channel_name", channel_name).execute()
            return response.data[0]["channel_id"] if response.data else False
        except Exception as e:
            logging.error("\nError %s during fetching channel in DB: %s\n", e, channel_name)
            return False

    async def fetch_channel_ids(self, channels: List[str]) -> List[int]:
        """
        Retrieve the IDs of channels with the given names from the database.

        :param channels: A list of channel names to fetch IDs for.
        :return: A list of channel IDs corresponding to the provided channel names.
        :raises: Logs an error if an exception occurs during the database operation.
        """
        try:
            response = self.client.table("channels").select("*").in_("channel_name", channels).execute()
            return [channel["channel_id"] for channel in response.data]
        except Exception as e:
            logging.error("\nError %s during fetching channels in DB: %s\n", e, channels)

    async def fetch_channel_name(self, channel_id: int) -> str:
        """
        Retrieve the channel name by its ID.

        :param channel_id: The ID of the channel to retrieve.
        :return: The name of the channel if found, otherwise False.
        """
        try:
            response = self.client.table("channels").select("channel_name").eq("channel_id", channel_id).single().execute()
            return response.data["channel_name"] if response.data else False
        except Exception as e:
            logging.error("\nError %s during fetching channel by id: %s\n", e, channel_id)
            return False

    @staticmethod
    async def generate_channel_hash(channel_name: str) -> int:
        """
        Generate a 63-bit integer hash for a given channel name using SHA-256.

        :param channel_name: The name of the channel to generate a hash for.
        :return: A 63-bit integer representing the hash of the channel name.
        """
        hash_bytes = hashlib.sha256(channel_name.encode("utf-8")).digest()[:8]
        hash_int = int.from_bytes(hash_bytes, byteorder='big', signed=False)
        return hash_int % (2**63)  # Ограничение до 63 бит
