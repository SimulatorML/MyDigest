import os
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.utils.text import safe_format_entities
from telethon import TelegramClient, errors
from typing import List, Dict, Union
from src.data.database import supabase
from src.data.database import SupabaseDB
from src.config.config import TELEGRAM_BOT_TOKEN, API_ID, API_HASH, PHONE_NUMBER, MISTRAL_KEY
from src.summarization import Summarization
from telethon.tl.types import Channel, Chat

TIME_RANGE_24H = timedelta(hours=24)
# DEFAULT_TIME_RANGE_HOURS = timedelta(hours=1)

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
                logging.info("\nНачинаем процесс авторизации...\n")
                # Запускаем процесс авторизации через номер телефона
                await client.start(phone=PHONE_NUMBER)
                await client.get_me()
                logging.info("\nАвторизация успешно завершена\n")
            else:
                logging.info("\nИспользуем существующую сессию\n")

            logging.info("\nTelethon client connected successfully\n")
        except Exception as e:
            logging.info("Ошибка при подключении к Telegram: %s", e)
            # Отключаем клиента, если произошла ошибка
            await client.disconnect()
            raise

        _telethon_client = client
        return _telethon_client

async def close_telethon_client():
    """Function to close telethon when the bot is shutting down"""
    global _telethon_client
    if _telethon_client and _telethon_client.is_connected():
        await _telethon_client.disconnect()
        _telethon_client = None

class TelegramScraper:
    running_tasks = {}

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db = SupabaseDB(supabase)
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.summarizer = Summarization(api_key=MISTRAL_KEY)

    @staticmethod
    async def get_entity(entity_name: str):
        """
               Retrieve a Telegram entity (such as a channel or user) by its name.

               This method fetches the Telegram entity based on the provided name. It first ensures that
               the client is connected before attempting the retrieval.

               :param entity_name: The username or channel name of the Telegram entity.
               :return: The Telegram entity object if found, otherwise None.
               :raises: Exception if retrieval fails.
               """
        client = await init_telethon_client()
        try:
            if not client.is_connected():
                await client.connect()
            entity = await client.get_entity(entity_name)
            return entity
        except Exception as e:
            logging.error("Error getting entity %s: %s", entity_name, e)
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
        client = await init_telethon_client()
        entity = await self.get_entity(entity_name)
        if not entity:
            return []
        
        # Проверяем, является ли сущность каналом или чатом
        if not isinstance(entity, (Channel, Chat)):
            logging.warning(f"Сущность {entity_name} не является каналом или чатом. Пропуск.")
            return []

        now = datetime.utcnow()
        start_time = now - TIME_RANGE_24H
        channel_title = entity.title

        messages = []
        while True:
            try:
                async for message in client.iter_messages(entity, limit=limit):
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
                logging.warning("\nFloodWait на {e.seconds} секунд...\n")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logging.error("Failed to scrape messages: %s", e)
                break
        return messages

    async def check_new_messages(self, user_id: int, time_range: timedelta):
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
                await self.bot.send_message(user_id, "❌ У вас нет добавленных каналов.")
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
                await asyncio.sleep(1)

            if aggregated_news:
                summaries = await self.summarizer.summarize_news_items(aggregated_news)
                digest = await self.summarizer.cluster_summaries(summaries)
                creation_timestamp = datetime.now().isoformat()
                await self.db.save_user_digest(user_id, digest, creation_timestamp)
                
                # Разбиваем на части сообщение
                digest_parts = await self._split_digest(digest) # обозначаем части сообщения (part)
                for index, part in enumerate(digest_parts, 1):

                    try:
                        # Проверяем валидность HTML
                        safe_text = safe_format_entities(part)
                    except Exception as e:
                        logging.error(f"Invalid HTML format: {e}")
                        safe_text = "❌ Ошибка форматирования сообщения"

                    prefix = f"<b>Часть {index} из {len(digest_parts)}</b>\n\n" if len(digest_parts) > 1 else ""
                    await self.bot.send_message(
                        user_id,
                        f"📢 <b>Ваш дайджест за последние {int(time_range.total_seconds() // 60)} минут:</b>\n{prefix}\n{safe_text}",
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                    await asyncio.sleep(1)  # Пауза между сообщениями

        except Exception as e:
            logging.error("Ошибка в check_new_messages: %s", e)

            error_message = str(e).lower()
            
            # chat not found
            if "chat not found" in error_message:
                logging.error(f"Чат с пользователем {user_id} не найден. ⚠️ Деактивация.")
                await self.db.set_user_receiving_news(user_id, False)  # Деактивируем
                TelegramScraper.stop_auto_news_check(user_id)  # Останавливаем задачи

            # При заблокированном боте
            elif "bot was blocked by the user" in error_message:
                logging.error(f"Пользователь {user_id} заблокировал бота. ⚠️ Деактивация.")
                await self.db.set_user_receiving_news(user_id, False)
                TelegramScraper.stop_auto_news_check(user_id)

            else:
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
        db = SupabaseDB(supabase)
        interval = await db.get_user_interval(user_id)
        logging.info("\n🔍 Запускаю фоновую проверку для пользователя %s (интервал %s мин)...\n", user_id, interval // 60)

        await self.db.cleanup_old_news()

        while user_id in TelegramScraper.running_tasks:
            logging.info("\n🔄 Проверка новых сообщений для %s...\n", user_id)
            await self.check_new_messages(user_id, time_range=timedelta(seconds=interval))  # Проверяем новые сообщения за последний час
            logging.info("\n✅ Проверка завершена %s. Следующая через %s минут.\n",
                         datetime.now().strftime('%Y-%m-%d %H:%M:%S'), interval // 60)

            await asyncio.sleep(interval)  # Ждем перед следующей проверкой

    @staticmethod
    def stop_auto_news_check(user_id: int):
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

    async def scrape_messages_long_term(self, entity_name: str, days: int = 2, limit: int = 1000) -> List[Dict[str, Union[int, str, datetime]]]:
        """
        Scrape messages from a specified Telegram channel within the past specified number of days.

        :param entity_name: The username or channel name of the Telegram entity.
        :param days: The number of days to look back for messages. Defaults to 2 days.
        :param limit: The maximum number of messages to scrape. Defaults to 1000.
        :return: A list of dictionaries, each containing:
                 - 'message_id': The unique ID of the message.
                 - 'message': The text content of the message.
                 - 'message_date': The timestamp of when the message was sent.
                 - 'channel_title': The title of the channel.
        :raises: Exception if message scraping fails.
        """
        client = await init_telethon_client()
        entity = await self.get_entity(entity_name)
        if not entity:
            return []

        now = datetime.utcnow()
        start_time = now - timedelta(days=days)

        channel_title = getattr(entity, 'title', 'Неизвестный канал')
        messages = []

        while True:
            try:
                async for message in client.iter_messages(entity, limit=limit):
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

                # Добавляем задержку между запросами
                await asyncio.sleep(1)

                break
            except errors.FloodWaitError as e:
                logging.warning("\nFloodWait на %s секунд...\n", e.seconds)
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logging.error("\nFailed to scrape messages: %s", e)
                break
        return messages

    ### Сплитер для сообщений
    async def _split_digest(self, text: str, max_length: int = 4096) -> list[str]:
        parts = []
        while text:
            # Ищем безопасное место для разбивки, чтобы не разрывать теги
            if len(text) <= max_length:
                parts.append(text)
                break

            # Ищем последний закрывающий тег в пределах max_length
            split_pos = text.rfind('</a>', 0, max_length)
            if split_pos != -1:
                split_pos += 4  # Включаем сам тег </a>
            else:
                # Если тегов нет, разбиваем по последнему переносу строки
                split_pos = text.rfind('\n', 0, max_length)
                if split_pos == -1:
                    # Если нет переносов, принудительно обрезаем
                    split_pos = max_length

            parts.append(text[:split_pos])
            text = text[split_pos:].lstrip()
        return parts