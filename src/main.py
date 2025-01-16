import sys
import logging
import asyncio

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from definitions import TELEGRAM_BOT_TOKEN

# State identifiers
UPDATE_SOURCES_STATE = "update_sources_state"

bot: Bot = None
router = Router()

@router.message(Command("start"))
async def start_handler(msg: Message):
    await msg.answer("Hello! It's MyDigest bot. I can help to collect you personal set of news sources and provide you daily digests.",
                     reply_markup=ReplyKeyboardRemove()) #ReplyKeyboardRemove need if we will use keyboard

@router.message(Command("menu"))
async def send_menu(msg: Message):
    await msg.answer("This is menu")

@router.message(Command("daily_digest"))
async def get_daily_digest(msg: Message):
    await msg.answer("This is daily digest")

@router.message(Command("weekly_digest"))
async def get_weekly_digest(msg: Message):
    await msg.answer("This is weekly digest")

@router.message(Command("update_sources"))
async def handle_update_sources(msg: Message, state: FSMContext):
    await state.set_state(UPDATE_SOURCES_STATE)
    await msg.answer("Please enter the channel names")

async def main():
    # TODO
    # Написать функцию init_postgres_pool, реализующую подключение к БД
    # pool = await init_postgres_pool(db link)

    bot = Bot(token=TELEGRAM_BOT_TOKEN) # if need markdown parse_mode=ParseMode.Mardown
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(router)

    # Start event dispatching
    await dp.start_polling(bot)

if __name__ == '__main__':
    # TODO 
    # Вынести настройки логгера в отдельный файл
    # Написать функции-декораторы для логирования сообщений/команд
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
