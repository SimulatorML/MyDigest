import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from src.commands import ALL_COMMANDS
from src.config import TELEGRAM_BOT_TOKEN
from src.handlers.channels import router as channels_router
from src.data.database import supabase, SupabaseDB
from src.scraper import TelegramScraper, init_telethon_client

db = SupabaseDB(supabase)

class DigestBot:
    def __init__(self):
        # Initialize bot and dispatcher
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())

        # Register routers
        self.dp.include_router(channels_router)

    def start(self):
        """Start the bot"""
        asyncio.run(self._start_polling())

    async def _start_polling(self):
        self.dp.startup.register(self._on_startup)
        self.dp.shutdown.register(self._on_shutdown)
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logging.error("Error during bot startup: %s", e)
            raise
        finally:
            await self.bot.session.close()


    async def _on_startup(self, bot: Bot):
        """
        This is called when the bot starts up
        When the bot starts up, it retrieves users who are currently receiving news.
        It automatically starts the scraper once the bot is relaunched.
        """
        active_users = await db.retrieve_current_users()
        await bot.delete_my_commands()
        await bot.set_my_commands(ALL_COMMANDS)
        logging.info("Bot started successfully")

        await init_telethon_client()
        if active_users:
            for user in active_users.data:
                user_id = user["user_id"]
                scraper = TelegramScraper(user_id)
                task = asyncio.create_task(scraper.start_auto_news_check(user_id, interval=600))
                TelegramScraper.running_tasks[user_id] = task

        logging.info("Bot started successfully and tasks re-launched for active users")

    async def _on_shutdown(self, bot: Bot):
        logging.info("Bot is shutting down")
        await bot.session.close()


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    # Create and start bot
    digest_bot = DigestBot()
    digest_bot.start()
