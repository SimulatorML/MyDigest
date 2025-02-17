import asyncio
import re
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.scraper import TelegramScraper
from src.data.database import supabase
from src.data.database import SupabaseDB

# from src.data.database import (
#     fetch_user,
#     fetch_user_channels,
#     add_user,
#     add_user_channels,
#     delete_user_channels,
#     clear_user_channels,
#     # fetch_user_digests
#     # make_digest
# )


router = Router()
db = SupabaseDB(supabase)


class UserStates(StatesGroup):
    waiting_for_channels = State()
    waiting_for_delete = State()


@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(
        "Привет! Я бот для создания дайджестов из Telegram каналов.\n"
        "Используйте следующие команды:\n"
        "/add_channels - добавить каналы\n"
        "/show_channels - показать список ваших каналов\n"
        "/delete_channels - удалить каналы\n"
        "/clear_channels - полностью очистить список каналов\n"
        "/help - показать эту справку\n"
        # "/daily_digest - показать сводки новостей за день\n"
        "/receive_news - показывать сводки новостей за час\n"
    )
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "unknown"
    login_timestamp = datetime.now().isoformat()

    # Добавляем или обновляем пользователя
    user_exists = await db.fetch_user(user_id)
    if not user_exists:
        await db.add_user(user_id, username, login_timestamp)
        await message.answer("Вы успешно зарегистрированы!")
    else:
        await message.answer("Вы уже зарегистрированы!")
        # user_channels = await fetch_user_channels(user_id)
        # if user_channels:
        #     await make_digest(user_id)         # создание диджеста
        #     await message.answer("Дайджест создан.")
        #     await message.answer("Вот Дайджест из ваших каналов:\n")
        #     await fetch_user_digests(user_id)  # Вывод дайджеста


@router.message(Command(commands="help"))
async def process_help_command(message: Message):
    await message.answer(
        "Я помогу вам создавать дайджесты из выбранных Telegram каналов.\n\n"
        "Доступные команды:\n"
        "/add_channels - добавить каналы\n"
        "/show_channels - показать список ваших каналов\n"
        "/delete_channels - удалить каналы\n"
        "/clear_channels - полностью очистить список каналов\n"
        "/help - показать эту справку\n"
        # "/daily_digest - показать сводки новостей за день\n"
        "/receive_news - показывать сводки новостей за час\n"
    )


@router.message(Command(commands="add_channels"))
async def process_add_channels_command(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, отправьте список каналов для добавления в формате: @channel1 @channel2"
    )
    # Устанавливаем состояние ожидания ввода каналов
    await state.set_state(UserStates.waiting_for_channels)


# Обработчик для получения списка каналов
@router.message(UserStates.waiting_for_channels)
async def process_channels_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    channels_text = message.text.strip()
    addition_timestamp = datetime.now().isoformat()

    if not channels_text:
        await message.answer("Пожалуйста, отправьте корректный список каналов.")
        return

    new_channels = {ch.strip() for ch in channels_text.split() if ch.strip()}

    if not all(re.match(r"^@[A-Za-z0-9_]+$", ch) for ch in new_channels):
        await message.answer(
            "Все каналы должны начинаться с одного символа '@', не содержать знаков препинания в конце названия и быть разделены пробелом. Попробуйте снова."
        )
        return

    success = await db.add_user_channels(user_id, new_channels, addition_timestamp)
    if success:
        await message.answer(f"Каналы добавлены: {', '.join(new_channels)}")
        # user_channels = await fetch_user_channels(user_id)
        # if user_channels:
        #     await make_digest(user_id)
        # await message.answer("Дайджест создан.")
        # await message.answer("Вот Дайджест из ваших каналов:\n")
        # await print(fetch_user_digests(user_id))  # Вывод дайджеста
    else:
        await message.answer("Произошла ошибка при добавлении каналов.")
    # Сбрасываем состояние
    await state.clear()


@router.message(Command(commands="show_channels"))
async def process_show_channels_command(message: Message):
    user_id = message.from_user.id
    channels = await db.fetch_user_channels(user_id)

    if channels is not None:
        channel_names = [channel["channel_name"] for channel in channels]
        await message.answer(f"Ваши каналы:\n{', '.join(channel_names)}")
    else:
        await message.answer("У вас пока нет добавленных каналов.")


@router.message(Command(commands="delete_channels"))
async def process_delete_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    channels = await db.fetch_user_channels(user_id)

    if not channels:
        await message.answer("У вас нет добавленных каналов для удаления.")
        return

    channel_names = [channel["channel_name"] for channel in channels]
    await message.answer(
        f"Текущий список ваших каналов:\n"
        f"{', '.join(channel_names)}\n\n"
        f"Введите канал или список каналов для удаления (например: @channel1 @channel2)"
    )
    await state.set_state(UserStates.waiting_for_delete)


@router.message(UserStates.waiting_for_delete)
async def process_delete_channels(message: Message, state: FSMContext):
    user_id = message.from_user.id

    channels_to_delete = {ch.strip() for ch in message.text.split() if ch.strip()}

    if not all(re.match(r"^@[A-Za-z0-9_]+$", ch) for ch in channels_to_delete):
        await message.answer(
            "Все каналы должны начинаться с одного символа '@', не содержать знаков препинания в конце названия и быть разделены пробелом. Попробуйте снова."
        )
        return

    await db.delete_user_channels(user_id, channels_to_delete)
    await message.answer(f"Каналы удалены: {', '.join(channels_to_delete)}")
    await state.clear()


@router.message(Command(commands="clear_channels"))
async def process_clear_command(message: Message):
    user_id = message.from_user.id
    await db.clear_user_channels(user_id)
    await message.answer("Все каналы удалены.")


# @router.message(Command("daily_digest"))
# async def daily_digest(message: Message) -> None:
#     user_id = message.from_user.id
#     digest = await make_digest(user_id, "24h")
#     if digest:
#         await message.answer("Дневной дайджест новостей:\n\n")
#         await fetch_user_digests(user_id)
#     else:
#         await message.answer("Не найдено ни одного сообщения для ежедневного дайджеста.")


@router.message(Command("receive_news"))
async def receive_news_handler(message: Message):
    interval = 300  # modifiable
    divider = 60    # modifiable

    user_id = message.from_user.id
    scraper = TelegramScraper(user_id)

    if scraper.stop_auto_news_check(user_id):
        await message.answer("🔄 Перезапускаю фоновую проверку новостей...")

    task = asyncio.create_task(scraper.start_auto_news_check(user_id, interval=interval))   #1800 было
    scraper.running_tasks[user_id] = task

    # logger.info(f"Фоновая проверка новостей запущена для пользователя {user_id}.")
    await message.answer(f"✅ Фоновая проверка новостей запущена. Вы будете получать обновления каждые {interval // divider} минут.")


# Хэндлер для всех остальных сообщений
@router.message()
async def process_other_messages(message: Message):
    await message.answer(
        "Я понимаю только команды. Используйте /help, "
        "чтобы увидеть список доступных команд."
    )
