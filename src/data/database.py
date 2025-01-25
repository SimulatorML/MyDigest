from datetime import datetime
from src.config.config import supabase
from supabase import AuthApiError, PostgrestAPIError


class SupabaseErrorHandler:
    @staticmethod
    def handle_auth_error(e, user_id):
        print(f"Ошибка аутентификации для пользователя {user_id}: {e}")

    @staticmethod
    def handle_api_error(e, user_id):
        print(f"Ошибка API для пользователя {user_id}: {e}")

    @staticmethod
    def handle_general_error(e, user_id):
        print(f"Произошла ошибка для пользователя {user_id}: {e}")


async def add_user(user_id, username):
    """
    Add or update a user in the Supabase 'users' table.

    This function attempts to insert or update a user's information in the database.
    It includes the user_id, username, and the current login timestamp. If successful,
    it prints a confirmation message. If unsuccessful, it prints an error message and 
    returns an empty list.

    :param user_id: The ID of the user to add or update.
    :param username: The username of the user to add or update.
    :return: The response data from the database operation, or an empty list in case of an error.
    """

    try:
        login_timestamp = datetime.now()
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

        if response.status_code == 201:
            print("Пользователь успешно добавлен или обновлен.")
        else:
            print(f"Ошибка при добавлении пользователя: {response.data}")

        return response.data
    except AuthApiError as e:
        SupabaseErrorHandler.handle_auth_error(e, user_id)
        return []
    except PostgrestAPIError as e:
        SupabaseErrorHandler.handle_api_error(e, user_id)
        return []
    except Exception as e:
        SupabaseErrorHandler.handle_general_error(e, user_id)
        return []


async def fetch_user_channels(user_id):
    """
    Get a list of all channels for a given user_id from the database.

    :param user_id: The ID of the user to fetch channels for.
    :return: A list of dictionaries where each dictionary represents a channel
    and contains the keys "id", "user_id", and "channel_name".
    """
    try:
        response = (
            supabase.table("user_channels")
            .select("channel_name")
            .eq("user_id", user_id)
            .execute()
        )
        return response.data
    except AuthApiError as e:
        SupabaseErrorHandler.handle_auth_error(e, user_id)
        return []
    except PostgrestAPIError as e:
        SupabaseErrorHandler.handle_api_error(e, user_id)
        return []
    except Exception as e:
        SupabaseErrorHandler.handle_general_error(e, user_id)
        return []


async def add_user_channels(user_id, channels):
    """
    Add channels to the database for a given user.

    :param user_id: The ID of the user to add channels for.
    :param channels: A list of strings representing the channels to add.
    :return: A list of dictionaries where each dictionary represents a channel
    and contains the keys "id", "user_id", "channel_name", and "channel_link".
    """
    try:
        data = []
        for channel in channels:
            channel_name = channel if channel.startswith("@") else None
            channel_link = channel if channel.startswith("t.me/") else None
            data.append(
                {
                    "user_id": user_id,
                    "channel_name": channel_name,
                    "channel_link": channel_link,
                    "addition_timestamp": datetime.now(),
                }
            )
        response = supabase.table("user_channels").insert(data).execute()

        if response.status_code == 201:
            print("Данные о пользователях и их каналах успешно записаны в базу данных.")
        else:
            print(f"Ошибка при записи данных: {response.data}")

        return response.data
    except AuthApiError as e:
        SupabaseErrorHandler.handle_auth_error(e, user_id)
    except PostgrestAPIError as e:
        SupabaseErrorHandler.handle_api_error(e, user_id)
    except Exception as e:
        SupabaseErrorHandler.handle_general_error(e, user_id)


async def delete_user_channels(user_id, channels):
    """
    Delete channels from the database for a given user.

    :param user_id: The ID of the user to delete channels for.
    :param channels: A list of strings representing the channels to delete.
    :return: A boolean indicating whether the deletion was successful.
    """
    try:
        for channel in channels:
            supabase.table("user_channels").delete().eq("user_id", user_id).eq(
                "channel_name", channel
            ).execute()
        return True
    except AuthApiError as e:
        SupabaseErrorHandler.handle_auth_error(e, user_id)
    except PostgrestAPIError as e:
        SupabaseErrorHandler.handle_api_error(e, user_id)
    except Exception as e:
        SupabaseErrorHandler.handle_general_error(e, user_id)


async def clear_user_channels(user_id):
    """
    Clear all channels associated with a given user from the database.

    :param user_id: The ID of the user whose channels are to be cleared.
    :return: The response data from the database operation.
    """

    try:
        response = (
            supabase.table("user_channels").delete().eq("user_id", user_id).execute()
        )
        return response.data
    except AuthApiError as e:
        SupabaseErrorHandler.handle_auth_error(e, user_id)
    except PostgrestAPIError as e:
        SupabaseErrorHandler.handle_api_error(e, user_id)
    except Exception as e:
        SupabaseErrorHandler.handle_general_error(e, user_id)
