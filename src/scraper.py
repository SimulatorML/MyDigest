import os.path
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from telethon import TelegramClient, errors
from typing import List, Dict, Union
from src.data.database import supabase
from src.data.database import SupabaseDB
from src.config.config import TELEGRAM_BOT_TOKEN, API_ID, API_HASH, PHONE_NUMBER, MISTRAL_KEY
from src.summarization import Summarization

def create_client():
    session_path = os.path.join(os.getcwd(), 'sessions', "bot_session")
    os.makedirs('sessions', exist_ok=True)
    
    client = TelegramClient(
        session_path,
        API_ID,
        API_HASH
    )
    return client

class TelegramScraper:
    _client = None
    running_tasks = {}
    is_initialized = False

    def __init__(self, user_id):
        self.user_id = user_id
        self.db = SupabaseDB(supabase)
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.summarizer = Summarization(api_key=MISTRAL_KEY)

    async def ensure_client_initialized(self):
        """Инициализация клиента при первой необходимости"""
        if not self.is_initialized:
            if self._client is None:
                self._client = create_client()
            await self.connect()
            self.is_initialized = True
        self.client = self._client

    async def connect(self):
        """Подключение к Telegram если еще не подключены"""
        try:
            if not self._client.is_connected():
                await self._client.connect()
            
            if not await self._client.is_user_authorized():
                print("Начинаем процесс авторизации...")
                await self._client.start(phone=PHONE_NUMBER)
                await self._client.get_me()
                print("Авторизация успешно завершена")
            else:
                print("Используем существующую сессию")
                
            print("Telethon client connected successfully")
            return True
        except Exception as e:
            print(f"Ошибка при подключении к Telegram: {e}")
            return False

    async def get_entity(self, entity_name):
        """Fetches a Telegram entity (such as a channel or user) by its name."""
        try:
            if not self.client.is_connected():
                await self.connect()
            
            entity = await self.client.get_entity(entity_name)
            return entity
        except Exception as e:
            logging.error(f"Error getting entity {entity_name}: {e}")
            return None

    async def scrape_messages(self, entity_name: str, limit: int = 400, time_range: str = "24h") -> List[
        Dict[str, Any]]:
        """
        Scrapes messages from a given Telegram channel within a specified time range.
        Args:
            entity_name (str): The username or channel name of the Telegram entity.
            limit (int, optional): The maximum number of messages to scrape. Defaults to 400.
            time_range (str, optional): The time range for filtering messages.
                                        Accepts "24h" for the last 24 hours or "7d" for the last 7 days.
                                        Defaults to "24h".
        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary contains:
                - 'message_id' (int): The unique ID of the message.
                - 'message' (str): The text content of the message.
                - 'message_date' (datetime): The timestamp of when the message was sent.
            Returns an empty list if no messages are found or an error occurs.
        """
        entity = await self.get_entity(entity_name)
        if not entity:
            return []

        now = datetime.utcnow()
        start_time = now - timedelta(hours=24) if time_range == "24h" else now - timedelta(days=7)

        messages = []
        try:
            async for message in self.client.iter_messages(entity, limit=limit):
                message_date_naive = message.date.replace(tzinfo=None)
                if message_date_naive >= start_time:
                    messages.append({
                        "message_id": message.id,
                        "message": message.text,
                        "message_date": message.date
                    })
                else:
                    break
        except errors.FloodWaitError as e:
            print(f'Have to sleep {e.seconds} seconds')
            await asyncio.sleep(e.seconds)
            return await self.scrape_messages(entity_name, limit, time_range)
        except Exception as e:
            print(f"Failed to scrape messages: {e}")

        return messages

    async def check_new_messages(self, user_id: int, time_range: str = "1h"):
        """Проверяет новые сообщения и отправляет дайджест пользователю."""
        try:
            user_channels = await self.db.fetch_user_channels(user_id)
            if not user_channels:
                await self.bot.send_message(user_id, "❌ У вас нет добавленных каналов. Используйте /add_channels.")
                return

            now = datetime.utcnow()
            start_time = now - timedelta(hours=1) if time_range == "1h" else now - timedelta(minutes=30)
            aggregated_news = []

            for channel in user_channels:
                messages = await self.scrape_messages(channel["channel_name"], limit=100)
                if not messages:
                    continue

                recent_messages = [
                    msg for msg in messages if msg["message_date"].replace(tzinfo=None) >= start_time
                ]

                for msg in recent_messages:
                    await self.db.save_channel_news(channel["channel_id"], msg["message"],
                                                    msg["message_date"].isoformat())

                    aggregated_news.append({
                        "channel": channel["channel_name"].lstrip("@"),
                        "message": msg["message"],
                        "message_id": msg["message_id"]
                    })
                await asyncio.sleep(3)

            if aggregated_news:
                digest = self.summarizer.summarize(aggregated_news)
                creation_timestamp = datetime.now().isoformat()
                await self.db.save_user_digest(user_id, digest, creation_timestamp)
                await self.bot.send_message(user_id, f"📢 Ваш дайджест:\n\n{digest}")

        except Exception as e:
            logging.error(f"Ошибка в check_new_messages: {e}")
            await self.bot.send_message(user_id, "❌ Ошибка при получении дайджеста. Попробуйте позже.")

    async def start_auto_news_check(self, user_id: int, interval: int = 1800):
        """Фоновая проверка сообщений для конкретного пользователя каждые N секунд."""
        print(f"🔍 Запускаю фоновую проверку для пользователя {user_id} (интервал {interval // 60} мин)...")

        # очистка старых новостей из таблицы channels_news при запуске проверки
        await self.db.cleanup_old_news()

        while user_id in TelegramScraper.running_tasks:
            print(f"🔄 Проверка новых сообщений для {user_id}...")
            await self.check_new_messages(user_id, time_range="1h")  # Проверяем новые сообщения за последний час
            print(f"✅ Проверка завершена {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Следующая через {interval // 60} минут.")
            await asyncio.sleep(interval)  # Ждем перед следующей проверкой

    def stop_auto_news_check(self, user_id: int):
        """Останавливает фоновую проверку новостей для пользователя."""
        if user_id in TelegramScraper.running_tasks:
            TelegramScraper.running_tasks[user_id].cancel()
            del TelegramScraper.running_tasks[user_id]
            return True
        return False
