import os
from dotenv import load_dotenv
from supabase import create_client, Client


def test_supabase_connection():
    try:
        load_dotenv()

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY not found in '.env'")

        # create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)

        # Test table query
        response = supabase.table("user_channels").select("*").limit(2).execute()
        print("Connection to Supabase successful!")
        print(f"The test request has been executed successfully. Response: {response}")
        return True

    except Exception as e:
        print(f"Error connecting to Supabase: {str(e)}")
        return False


if __name__ == "__main__":
    test_supabase_connection()
