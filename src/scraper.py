import os
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
DEFAULT_TIME_RANGE_HOURS = timedelta(hours=1)

_telethon_client: TelegramClient | None = None
_telethon_init_lock = asyncio.Lock()

async def init_telethon_client() -> TelegramClient:
    """
    Создает\возвращает уже созданный Telethon-клиент.
    """
    global _telethon_client
    # Блокируем доступ к клиенту с помощью _telethon_init_lock, чтобы избежать создания нескольких клиентов одновременно
    async with _telethon_init_lock:
        # Если уже есть клиент и он подключен — возвращаем
        if _telethon_client and _telethon_client.is_connected():
            return _telethon_client

        # Иначе создаем новый, если его нет
        session_path = os.path.join(os.getcwd(), 'sessions', "bot_session")
        os.makedirs('sessions', exist_ok=True)

        client = TelegramClient(session_path, API_ID, API_HASH)

        try:
            await client.connect()
            # Проверяем, авторизован ли пользователь
            if not await client.is_user_authorized():
                print("Начинаем процесс авторизации...")
                # Запускаем процесс авторизации через номер телефона
                await client.start(phone=PHONE_NUMBER)
                await client.get_me()
                print("Авторизация успешно завершена")
            else:
                print("Используем существующую сессию")

            print("Telethon client connected successfully")
        except Exception as e:
            print(f"Ошибка при подключении к Telegram: {e}")
            # Отключаем клиента, если произошла ошибка
            await client.disconnect()
            raise

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
                            "message_date": message.date,
                            "channel_title": channel_title
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

    async def check_new_messages(self, user_id: int, time_range: DEFAULT_TIME_RANGE_HOURS):
        """
        Check for new messages from channels associated with the user and send a digest.

        This method retrieves the user's channels from the database, scrapes recent messages from each channel
        within the specified time range, saves them to the database, and then creates and sends a digest to the user.

        :param user_id: The unique identifier of the user.
        :param time_range: The time range (as timedelta) to consider for new messages.
        :return: None.
        :raises: Exception if checking messages or sending the digest fails.
        """
        try:
            user_channels = await self.db.fetch_user_channels(user_id)
            if not user_channels:
                await self.bot.send_message(user_id, "❌ У вас нет добавленных каналов. Используйте /add_channels.")
                return

            now = datetime.utcnow()
            start_time = now - time_range
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
                        "message_id": msg["message_id"],
                        "channel_title": msg.get("channel_title", channel["channel_name"].lstrip("@"))
                    })
                await asyncio.sleep(3)

            if aggregated_news:
                summaries = self.summarizer.summarize_news_items(aggregated_news)
                digest = self.summarizer.cluster_summaries(summaries)
                creation_timestamp = datetime.now().isoformat()
                await self.db.save_user_digest(user_id, digest, creation_timestamp)
                await self.bot.send_message(user_id,
                                            f"📢 <b> Ваш дайджест за последний час: </b>\n\n{digest}",
                                            parse_mode="HTML")

        except Exception as e:
            logging.error(f"Ошибка в check_new_messages: {e}")
            await self.bot.send_message(user_id, "❌ Ошибка при получении дайджеста. Попробуйте позже.")

    async def start_auto_news_check(self, user_id: int, interval: int = 1800):
        """
        Start a background task to periodically check for new messages and update the user's digest.

        This method initiates a continuous background loop that, at every interval, checks for new messages
        across the user's subscribed channels, updates the digest, and cleans up old news from the database.

        :param user_id: The unique identifier of the user.
        :param interval: The time interval in seconds between successive checks. Defaults to 1800 seconds (30 minutes).
        :return: None.
        :raises: Exception if the background task fails to start.
        """
        logging.info(f"🔍 Запускаю фоновую проверку для пользователя {user_id} (интервал {interval // 60} мин)...")

        # очистка старых новостей из таблицы channels_news при запуске проверки
        await self.db.cleanup_old_news()

        while user_id in TelegramScraper.running_tasks:
            logging.info(f"\n🔄 Проверка новых сообщений для {user_id}...\n")
            await self.check_new_messages(user_id, time_range=DEFAULT_TIME_RANGE_HOURS)  # Проверяем новые сообщения за последний час
            logging.info(f"\n✅ Проверка завершена {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. "
                         f"Следующая через {interval // 60} минут.\n")

            await asyncio.sleep(interval)  # Ждем перед следующей проверкой

    def stop_auto_news_check(self, user_id: int):
        """
        Stop the background task checking for new messages for the specified user.

        This method cancels the background task associated with the user, effectively stopping
        further periodic message checks and digest updates.

        :param user_id: The unique identifier of the user.
        :return: True if the background task was successfully stopped, otherwise False.
        :raises: Exception if stopping the task fails.
        """
        if user_id in TelegramScraper.running_tasks:
            TelegramScraper.running_tasks[user_id].cancel()
            del TelegramScraper.running_tasks[user_id]
            return True
        return False
