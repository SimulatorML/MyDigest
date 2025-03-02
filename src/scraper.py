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

TIME_RANGE_24H = timedelta(hours=24)
DEFAULT_TIME_RANGE_HOURS = timedelta(hours=1) # Значение по умолчанию для check_new_messages

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
        self.client = None

    async def ensure_client_initialized(self):
        """
        Initialize the Telegram client if it is not already initialized.

        The method checks whether the client is already initialized. If not, it creates the client,
        connects to the Telegram network, and marks the initialization as complete.

        :return: None.
        :raises: Exception if client initialization or connection fails.
        """
        if not self.is_initialized:
            if self._client is None:
                self._client = create_client()
            await self.connect()
            self.is_initialized = True
        self.client = self._client

    async def connect(self):
        """
        Connect to the Telegram network using the Telethon client.

        This method checks if the client is connected; if not, it connects and handles the user authorization.
        If the user is not authorized, it starts the authorization process.

        :return: True if the client is connected successfully, otherwise False.
        :raises: Exception if connection or authorization fails.
        """
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
        """
        Retrieve a Telegram entity (such as a channel or user) by its name.

        This method fetches the Telegram entity based on the provided name. It first ensures that
        the client is connected before attempting the retrieval.

        :param entity_name: The username or channel name of the Telegram entity.
        :return: The Telegram entity object if found, otherwise None.
        :raises: Exception if retrieval fails.
        """
        try:
            if not self.client.is_connected():
                await self.connect()
            
            entity = await self.client.get_entity(entity_name)
            return entity
        except Exception as e:
            logging.error(f"Error getting entity {entity_name}: {e}")
            return None

    async def scrape_messages(self, entity_name: str, limit: int = 1000) -> List[Dict[str, Union[int, str, datetime]]]:
        """
        Scrape messages from a specified Telegram channel within the past 24 hours.

        The method retrieves the specified Telegram entity and iterates through its messages.
        Only messages sent within the last 24 hours are collected. In case of a FloodWaitError,
        it will wait for the specified duration before retrying.

        :param entity_name: The username or channel name of the Telegram entity.
        :param limit: The maximum number of messages to scrape. Defaults to 1000.
        :return: A list of dictionaries, each containing:
                 - 'message_id': The unique ID of the message.
                 - 'message': The text content of the message.
                 - 'message_date': The timestamp of when the message was sent.
                 - 'channel_title': The title of the channel.
        :raises: Exception if message scraping fails.
        """
        entity = await self.get_entity(entity_name)
        if not entity:
            return []

        now = datetime.utcnow()
        start_time = now - TIME_RANGE_24H

        channel_title = entity.title

        messages = []
        while True:
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
                break
            except errors.FloodWaitError as e:
                logging.warning(f"FloodWait на {e.seconds} секунд...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logging.error(f"Failed to scrape messages: {e}")
                break
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
                    msg for msg in messages
                    if msg["message_date"].replace(tzinfo=None) >= start_time
                ]

                for msg in recent_messages:
                    await self.db.save_channel_news(channel["channel_id"],
                                                    msg["message"],
                                                    msg["message_date"].isoformat()
                                                    )

                    aggregated_news.append({
                        "channel": channel["channel_name"].lstrip("@"),
                        "message": msg["message"],
                        "message_id": msg["message_id"]
                    })
                await asyncio.sleep(3)

            if aggregated_news:
                summaries = self.summarizer.summarize_news_items(aggregated_news)
                digest = self.summarizer.cluster_summaries(summaries)
                creation_timestamp = datetime.now().isoformat()
                await self.db.save_user_digest(user_id, digest, creation_timestamp)
                await self.bot.send_message(user_id, f"📢 <b> Ваш дайджест за последний час: </b>\n\n{digest}", parse_mode="HTML")

        except Exception as e:
            logging.error(f"Ошибка в check_new_messages: {e}")
            await self.bot.send_message(user_id, "❌ Ошибка при получении дайджеста. Попробуйте позже.")

    async def start_auto_news_check(self, user_id: int, interval: int = 1800):
        """Фоновая проверка сообщений для конкретного пользователя каждые N секунд."""
        logging.info(f"🔍 Запускаю фоновую проверку для пользователя {user_id} (интервал {interval // 60} мин)...")

        # очистка старых новостей из таблицы channels_news при запуске проверки
        await self.db.cleanup_old_news()

        while user_id in TelegramScraper.running_tasks:
            logging.info(f"\n🔄 Проверка новых сообщений для {user_id}...\n")
            await self.check_new_messages(user_id, time_range="1h")  # Проверяем новые сообщения за последний час
            logging.info(f"\n✅ Проверка завершена {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. "
                         f"Следующая через {interval // 60} минут.\n")

            await asyncio.sleep(interval)  # Ждем перед следующей проверкой

    def stop_auto_news_check(self, user_id: int):
        """Останавливает фоновую проверку новостей для пользователя."""
        if user_id in TelegramScraper.running_tasks:
            TelegramScraper.running_tasks[user_id].cancel()
            del TelegramScraper.running_tasks[user_id]
            return True
        return False
