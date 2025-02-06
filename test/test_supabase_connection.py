import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client


def test_supabase_connection():
    """
    Tests the connection to the Supabase instance by making a few example requests.

    The test is successful if the following conditions are met:
    - The upsert request to the users table has been executed successfully.
    - The select request from the users table has been executed successfully.
    - The upsert request to the user_channels table has been executed successfully.
    - The select request from the user_channels table has been executed successfully.

    Returns:
        bool: True if the connection to Supabase is successful, False otherwise.
    """
    try:
        load_dotenv()

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY not found in '.env'")

        # create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)

        data_users = {
            "user_id": 123456,
            "username": "username_2",
            "login_timestamp": datetime.now().isoformat(),
        }
        data_channel = {
            "user_id": 123456,
            "channel_name": "channel_name_1",
            "channel_link": "channel_link_1",
            "addition_timestamp": datetime.now().isoformat(),
        }
        # Test table query
        response_1 = supabase.table("users").upsert(data_users).execute()
        response_2 = supabase.table("users").select("*").limit(3).execute()
        response_3 = supabase.table("user_channels").upsert(data_channel).execute()
        response_4 = supabase.table("user_channels").select("*").limit(3).execute()

        print("Connection to Supabase successful!\n")
        print(
            f"The test upsert-1 has been executed successfully. Response: {response_1}\n"
        )
        print(
            f"The test request-2 has been executed successfully. Response: {response_2}\n"
        )
        print(
            f"The test upsert-3 has been executed successfully. Response: {response_3}\n"
        )
        print(
            f"The test request-4 has been executed successfully. Response: {response_4}\n"
        )
        return True

    except Exception as e:
        print(f"Error connecting to Supabase: {str(e)}")
        return False


if __name__ == "__main__":
    test_supabase_connection()
