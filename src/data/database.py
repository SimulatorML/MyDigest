from src.config.config import supabase
from supabase import AuthApiError, PostgrestAPIError


class SupabaseErrorHandler:
    """
    A class for handling Supabase errors. It contains three methods, each of which
    handles a specific type of error: authentication errors, API errors, and general
    errors. Each method prints a message to the console that includes a description
    of the error and the user ID associated with the error.
    """

    @staticmethod
    def handle_auth_error(e, user_id):
        print(f"Ошибка аутентификации для пользователя {user_id}: {e}")

    @staticmethod
    def handle_api_error(e, user_id):
        print(f"Ошибка API для пользователя {user_id}: {e}")

    @staticmethod
    def handle_general_error(e, user_id):
        print(f"Произошла ошибка для пользователя {user_id}: {e}")


async def fetch_user(user_id):
    """
    Get a user from the database by their ID.

    :param user_id: The ID of the user to fetch.
    :return: A dictionary representing the user, or None if the user could not be
             fetched.
    """
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return response.data
    except AuthApiError as e:
        SupabaseErrorHandler.handle_auth_error(e, user_id)
        return None
    except PostgrestAPIError as e:
        SupabaseErrorHandler.handle_api_error(e, user_id)
        return None
    except Exception as e:
        SupabaseErrorHandler.handle_general_error(e, user_id)
        return None


async def add_user(user_id, username, login_timestamp=None):
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
        if response.status_code in [200, 201]:
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
    and contains the keys "channel_id", "user_id", "channel_name", "channel_link",
    and "addition_timestamp".
    """
    try:
        response = (
            supabase.table("user_channels").select("*").eq("user_id", user_id).execute()
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


async def add_user_channels(user_id, channels, addition_timestamp=None):
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

        if response.status_code in [200, 201]:
            print("Данные о пользователях и их каналах успешно записаны в базу данных.")
            return True
        else:
            print(f"Ошибка при записи данных: {response.data}")
            return False
    except AuthApiError as e:
        SupabaseErrorHandler.handle_auth_error(e, user_id)
    except PostgrestAPIError as e:
        SupabaseErrorHandler.handle_api_error(e, user_id)
    except Exception as e:
        SupabaseErrorHandler.handle_general_error(e, user_id)
    return False


async def delete_user_channels(user_id, channels):
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
        supabase.table("user_channels").delete().eq("user_id", user_id).execute()
        return True
    except AuthApiError as e:
        SupabaseErrorHandler.handle_auth_error(e, user_id)
    except PostgrestAPIError as e:
        SupabaseErrorHandler.handle_api_error(e, user_id)
    except Exception as e:
        SupabaseErrorHandler.handle_general_error(e, user_id)
