import asyncio
from datetime import datetime
from typing import List, Dict, Any
from supabase import create_client, Client
from supabase import AuthApiError, PostgrestAPIError
from src.config.config import SUPABASE_URL, SUPABASE_KEY
from src.scraper import scrape_messages
from src.summarization import summarize


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class SupabaseErrorHandler:
    @staticmethod
    def handle_error(e: Exception, user_id: int) -> None:
        error_map = {
            AuthApiError: ("AuthError", 500),
            PostgrestAPIError: ("ApiError", 400),
            ConnectionError: ("ConnectionError", 503),
        }
        msg = f"{error_map.get(type(e))[0]} у пользователя {user_id}: {str(e)}"
        print(msg)  # В будущем заменить на логирование


async def fetch_user(user_id: int) -> int:
    """
    Get a user from the database by their ID.

    :param user_id: The ID of the user to fetch.
    :return: A dictionary representing the user, or None if the user could not be
             fetched.
    """
    try:
        response = (
            supabase.table("users").select("user_id").eq("user_id", user_id).execute()
        )
        return (
            response.data[0]["user_id"] if response.data else None
        )  # Return only user_id value
    except Exception as e:
        SupabaseErrorHandler.handle_error(e, user_id)


async def add_user(
    user_id: int, username: str, login_timestamp: str = None
) -> Dict[str, Any]:
    """
    Add a user to the database.

    :param user_id: The ID of the user to add.
    :param username: The username of the user to add.
    :param login_timestamp: The timestamp of the user's last login. Defaults to None.
    :return: The response data from the database operation.
    """
    try:
        response = (
            supabase.table("users")
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
        SupabaseErrorHandler.handle_error(e, user_id)


async def fetch_user_channels(user_id: int) -> Dict[str, Any]:
    """
    Get a list of all channels for a given user_id from the database.

    :param user_id: The ID of the user to fetch channels for.
    :return: A list of dictionaries where each dictionary represents a channel
    and contains the keys "channel_id", "user_id", "channel_name", "channel_link",
    and "addition_timestamp".
    """
    try:
        response = (
            supabase.table("user_channels").select("*").eq("user_id", user_id).execute()
        )
        return response.data if response.data else None
    except Exception as e:
        SupabaseErrorHandler.handle_error(e, user_id)


async def add_user_channels(
    user_id: int, channels: List[str], addition_timestamp: str = None
) -> bool:
    """
    Add channels for a given user to the database.

    :param user_id: The ID of the user to associate with the channels.
    :param channels: A set of channel names to add.
    :return: True if the operation was successful, False otherwise.
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

        response = supabase.table("user_channels").upsert(data).execute()

        if response.data:
            print("Данные о пользователях и их каналах успешно записаны в базу данных.")
            return True
        else:
            print(f"Ошибка при записи данных: {response.data}")
            return False
    except Exception as e:
        SupabaseErrorHandler.handle_error(e, user_id)


async def delete_user_channels(user_id: int, channels: List[str]) -> bool:
    """
    Delete specified channels associated with a given user from the database.

    :param user_id: The ID of the user whose channels are to be deleted.
    :param channels: A set of channel names to delete.
    :return: True if the operation was successful, otherwise handles exceptions.
    """
    try:
        for channel in channels:
            supabase.table("user_channels").delete().eq("user_id", user_id).eq(
                "channel_name", channel
            ).execute()
        return True
    except Exception as e:
        SupabaseErrorHandler.handle_error(e, user_id)


async def clear_user_channels(user_id: int) -> bool:
    """
    Clear all channels associated with a given user from the database.

    :param user_id: The ID of the user whose channels are to be cleared.
    :return: The response data from the database operation.
    """
    try:
        supabase.table("user_channels").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        SupabaseErrorHandler.handle_error(e, user_id)


# async def make_digest(user_id: int, time_range: str = "24h") -> None:
#     try:
#         exist_user = await fetch_user(user_id)
#         if not exist_user:
#             print(f"Пользователь {user_id} НЕ существует в БД")
#             return
#
#         user_channels = await fetch_user_channels(user_id) if exist_user else None
#
#         for channel in user_channels:
#             try:
#                 messages = await scrape_messages(
#                     channel["channel_name"], limit=5, time_range=time_range
#                 )  # scrape a limited numbers of messages from each channel over the last 24 hours
#                 if not messages:
#                     print(f"Нет сообщений для канала {channel['channel_name']}.")
#                     continue
#                 # if messages:
#                 digest_content = summarize(messages, channel["channel_name"])
#                 creation_timestamp = datetime.now().isoformat()
#                 await save_user_digest(
#                     user_id, channel["channel_id"], digest_content, creation_timestamp
#                 )
#
#             except Exception as e:
#                 print(f"Ошибка при создании дайджеста для пользователя {user_id}: {e}")
#
#     except Exception as e:
#         print(f"Ошибка при обработке канала {channel['channel_name']}: {e}")
#
#     finally:
#         # Даем время на завершение фоновых задач - тогда RuntimeWarning возникает реже
#         await asyncio.sleep(1)


async def save_user_digest(
    user_id: int, channel_id: int, digest_content: str, creation_timestamp: str = None
) -> bool:
    """
    Save a user's digest to the database.

    This function attempts to upsert a digest record for a given user and channel
    into the "digests" table. If the operation is successful, the function returns
    True. If the operation fails, it returns False and logs an error message.

    :param user_id: The ID of the user for whom the digest is being saved.
    :param channel_id: The ID of the channel associated with the digest.
    :param digest_content: The content of the digest to be saved.
    :param creation_timestamp: The timestamp of when the digest was created. Defaults to None.
    :return: True if the digest is successfully saved, False otherwise.
    """

    try:
        response = (
            supabase.table("digests")
            .upsert(
                {
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "content": digest_content,
                    "creation_timestamp": creation_timestamp,
                }
            )
            .execute()
        )
        if response.data:
            print("Дайджест успешно сохранён в базу данных.")
            return True
        else:
            print(f"Ошибка при записи дайджеста: {response.data}")
            return False
    except Exception as e:
        SupabaseErrorHandler.handle_error(e, user_id)


async def fetch_user_digests(user_id: int) -> List[str]:
    """
    Fetches all digests for a given user from the database.

    :param user_id: The ID of the user for whom to fetch digests.
    :return: A list of strings where each string is the content of a digest for the user.
    """
    try:
        response = (
            supabase.table("digests").select("content").eq("user_id", user_id).execute()
        )
        return [item["content"] for item in response.data] if response.data else None
    except Exception as e:
        SupabaseErrorHandler.handle_error(e, user_id)
