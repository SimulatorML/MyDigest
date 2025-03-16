import logging
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
                 Each dictionary contains the keys "user_id", "channel_name", and "addition_timestamp".
        :raises: SupabaseErrorHandler if an error occurs.
        """
        try:
            response = (
                self.client.table("user_channels")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_active", True)  # Берем только активные каналы
                .execute()
            )
            # return response.data if response.data else None
            data = response.data if response.data else []
            unique_channels = {channel["channel_name"]: channel for channel in data}
            return list(unique_channels.values())
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def fetch_all_user_channels(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all channels associated with a given user from the database, including inactive ones.

        :param user_id: The ID of the user whose channels are to be retrieved.
        :return: A list of dictionaries containing all the user's channels.
                 Each dictionary contains the keys "channel_id", "user_id", 
                 "channel_name", "channel_link", "addition_timestamp", "is_active".
        :raises: SupabaseErrorHandler if an error occurs.
        """
        try:
            response = (
                self.client.table("user_channels")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            # return response.data if response.data else None
            data = response.data if response.data else []
            unique_channels = {channel["channel_name"]: channel for channel in data}
            return list(unique_channels.values())
        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)

    async def add_user_channels(
        self, user_id: int, channels: List[str], addition_timestamp: str = None, channel_topics: List[str] = None
    ) -> bool:
        """
        Add new channels to a user's list and update existing ones.

        :param user_id: The ID of the user whose channels are to be added or updated.
        :param channels: A list of channel names to add or update.
        :param addition_timestamp: The timestamp of the addition operation.
                                   Defaults to the current time if not provided.
        :param channel_topics: A list of topics corresponding to each channel.
        :return: True if any channels were added or updated, otherwise False.
        :raises: SupabaseErrorHandler if an error occurs.
        """
        try:
            # Получаем список всех каналов, включая неактивные
            existing_channels = await self.fetch_all_user_channels(user_id)
            existing_names = {ch["channel_name"] for ch in existing_channels} if existing_channels else set()

            # Разделяем каналы на существующие и новые
            existing_to_update = [ch for ch in channels if ch in existing_names]
            new_to_add = [ch for ch in channels if ch not in existing_names]

            # Обновляем существующие каналы
            if existing_to_update:
                logging.info("\nОбновляем существующие каналы: %s\n", existing_to_update)
                # Обновить каналы, имеющие свои topics - активируй этот кусок
                response = self.client.table("user_channels").update({
                    "is_active": True,
                    "addition_timestamp": addition_timestamp
                }).eq("user_id", user_id).in_("channel_name", existing_to_update).execute()

                if not response.data:
                    logging.error("\nОшибка при обновлении существующих каналов: %s\n", response.error_message)
                    return False

                # Обновить каналы, НЕ имеющие своих topics - активируй этот кусок
                # for channel in existing_to_update:
                #     topic_index = channels.index(channel) if channel_topics else None
                #     topic = channel_topics[topic_index] if topic_index is not None else None
                #     response = self.client.table("user_channels").update({
                #         "is_active": True,      # True - активные, False - неактивные. Помечай как надо
                #         "channel_topic": topic
                #     }).eq("user_id", user_id).eq("channel_name", channel).execute()

                #     if not response.data:
                #         logging.error("\nОшибка при обновлении существующих каналов: %s\n", response.error_message)
                #         return False

            # Добавляем новые каналы
            if new_to_add:
                logging.info("\nДобавляем новые каналы: %s\n", new_to_add)
                new_data = [{
                    "user_id": user_id,
                    "channel_name": channel,
                    "channel_link": f"https://t.me/{channel[1:]}",
                    "addition_timestamp": addition_timestamp,
                    "is_active": True,
                    "channel_topic": channel_topics[channels.index(channel)] if channel_topics else None
                } for channel in new_to_add]

                if new_data:
                    response = self.client.table("user_channels").upsert(new_data).execute()
                    if not response.data:
                        logging.error("\nОшибка при добавлении новых каналов: %s\n", response.error_message)
                        return False

            return bool(existing_to_update or new_to_add)

        except Exception as e:
            SupabaseErrorHandler.handle_error(e, user_id, None)
            return False

    async def delete_user_channels(self, user_id: int, channels: List[str]) -> bool:
        """
        Delete specified channels from a given user in the database.

        :param user_id: The ID of the user whose channels are to be deleted.
        :param channels: A set of channel names to delete.
        :return: True if the operation was successful, otherwise handles exceptions.
        """
        try:
            response = self.client.table("user_channels").update(
                {"is_active": False}
            ).eq("user_id", user_id).in_("channel_name", channels).execute()

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
