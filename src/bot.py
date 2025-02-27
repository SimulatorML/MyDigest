import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from src.commands import ALL_COMMANDS
from src.config import TELEGRAM_BOT_TOKEN
from src.handlers.channels import router as channels_router
from src.scraper import TelegramScraper  # Добавляем импорт


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
        try:
            # Start polling
            await self.dp.start_polling(
                self.bot,
                on_startup=self._on_startup,
                on_shutdown=self._on_shutdown
            )
        except Exception as e:
            logging.error(f"Error during bot startup: {e}")
            raise
        finally:
            await self.bot.session.close()

    async def _on_startup(self, dp: Dispatcher):
        # Setup bot commands
        await self.bot.delete_my_commands()
        await self.bot.set_my_commands(ALL_COMMANDS)
        logging.info("Bot started successfully")

    async def _on_shutdown(self, dp: Dispatcher):
        """Shutdown handler"""
        logging.info("Bot is shutting down")
        await self.bot.session.close()


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
