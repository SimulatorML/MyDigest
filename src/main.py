import sys
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from definitions import TELEGRAM_BOT_TOKEN
from handlers.channels import router as channels_router

async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем роутер с командами
    dp.include_router(channels_router)
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    # TODO 
    # Вынести настройки логгера в отдельный файл
    # Написать функции-декораторы для логирования сообщений/команд
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())