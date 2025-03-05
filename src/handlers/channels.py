import asyncio
import re
import logging
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.scraper import TelegramScraper
from src.data.database import supabase
from src.data.database import SupabaseDB
from src.scraper import init_telethon_client


router = Router()
db = SupabaseDB(supabase)


class UserStates(StatesGroup):
    waiting_for_channels = State()
    waiting_for_delete = State()


############################## Приветствие ###############################
@router.message(CommandStart())
async def process_start_command(message: Message):
    sent_message = await message.answer(
        "Привет! Я бот для создания дайджестов из Telegram каналов.\n"
        "Используйте следующие команды:\n"
        "/add_channels - добавить каналы\n"
        "/show_channels - показать список ваших каналов\n"
        "/delete_channels - удалить каналы\n"
        "/clear_channels - полностью очистить список каналов\n"
        "/help - показать эту справку\n"
        "/receive_news - показывать сводки новостей за час\n"
    )

    # Закрепляем сообщение в шапке бота
    await message.chat.pin_message(sent_message.message_id)

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

############################## help - Показать справку #############################
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
        "/receive_news - показывать сводки новостей за час\n"
    )


############################## add_channels - Добавить каналы ######################
@router.message(Command(commands="add_channels"))
async def process_add_channels_command(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, отправьте список каналов для добавления в формате: @channel1 @channel2"
    )
    # Устанавливаем состояние ожидания ввода каналов
    await state.set_state(UserStates.waiting_for_channels)


### Обработчик для получения списка каналов
@router.message(UserStates.waiting_for_channels)
async def process_channels_input(message: Message, state: FSMContext):
    # Проверяем, является ли сообщение командой
    if message.text.startswith('/'):
        await state.clear()
        await message.answer("Вы отменили добавление каналов. Пожалуйста, повторите нужную вам команду")
        return

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
    else:
        await message.answer("Ошибка при добавлении каналов. Попробуйте еще раз.")

    # Сбрасываем состояние
    await state.clear()


############################## show_channels - Показать каналы #####################
@router.message(Command(commands="show_channels"))
async def process_show_channels_command(message: Message):
    user_id = message.from_user.id
    channels = await db.fetch_user_channels(user_id)

    if channels is not None:
        channel_names = [channel["channel_name"] for channel in channels]
        await message.answer(f"Ваши каналы:\n{', '.join(channel_names)}")
    else:
        await message.answer("У вас пока нет добавленных каналов.")


############################## delete_channels - Удалить каналы #################
# Обработчик для удаления каналов
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

    # Устанавливаем состояние ожидания ввода каналов
    await state.set_state(UserStates.waiting_for_delete)

## Состояние ожидания ввода каналов для удаления
@router.message(UserStates.waiting_for_delete)
async def process_delete_channels(message: Message, state: FSMContext):
    # Проверяем, является ли сообщение командой
    if message.text.startswith('/'):
        await state.clear()
        await message.answer("Вы отменили удаление каналов. Пожалуйста, повторите нужную вам команду")
        return

    user_id = message.from_user.id
    channels_to_delete = {ch.strip() for ch in message.text.split() if ch.strip()}

    if not all(re.match(r"^@[A-Za-z0-9_]+$", ch) for ch in channels_to_delete):
        await message.answer(
            "Все каналы должны начинаться с одного символа '@', не содержать знаков препинания в конце названия и быть разделены пробелом. Попробуйте снова."
        )
        return

    result = await db.delete_user_channels(user_id, channels_to_delete)
    if not result:
        await message.answer("Произошла ошибка при удалении каналов.")
        return

    await message.answer(f"Каналы удалены: {', '.join(channels_to_delete)}")
    # Сбрасываем состояние
    await state.clear()

## Обработчик для полной очистки каналов
@router.message(Command(commands="clear_channels"))
async def process_clear_command(message: Message):
    user_id = message.from_user.id
    result = await db.clear_user_channels(user_id)
    if not result:
        await message.answer("Произошла ошибка при очистке каналов.")
        return
    await message.answer("Все каналы удалены.")


############################## receive_news - Получить сводки новостей ############
@router.message(Command("receive_news"))
async def receive_news_handler(message: Message):
    interval = 600  # modifiable
    divider = 60    # modifiable

    user_id = message.from_user.id
    scraper = TelegramScraper(user_id)
    
    try:
        # Инициализируем клиент только при первом запросе
        await init_telethon_client()
        
        if scraper.stop_auto_news_check(user_id):
            await message.answer("🔄 Перезапускаю фоновую проверку новостей...")

        task = asyncio.create_task(scraper.start_auto_news_check(user_id, interval=interval))
        TelegramScraper.running_tasks[user_id] = task

        await message.answer(
            f"✅ Фоновая проверка новостей запущена. "
            f"Вы будете получать обновления каждые {interval // divider} минут."
        )
    except Exception as e:
        await message.answer("❌ Произошла ошибка при запуске проверки новостей. Попробуйте позже.")
        logging.error(f"Error in receive_news_handler: {e}")

##############################  FORWARD: Добавить каналы через пересылку #################
@router.message(lambda message: message.forward_from_chat.type == 'channel')
async def handle_forwarded_message(message: Message):
    
    user_id = message.from_user.id
    addition_timestamp = datetime.now().isoformat()
    channel = message.forward_from_chat.username

    if not channel:
        await message.answer("❌ Канал не определен. Пожалуйста, убедитесь, что вы пересылаете сообщение из публичного канала.")
        await message.delete()
        return

    if not channel.startswith("@"):
        channel = f"@{channel}"

    success = await db.add_user_channels(user_id, [channel], addition_timestamp)

    if success:
        await message.answer(f"Канал {channel} успешно добавлен! ✔️")
        await message.delete()
    else:
        await message.answer("Произошла ошибка при добавлении канала. Пожалуйста, попробуйте позже.")
        await message.delete()
        return


# # Хэндлер для всех остальных сообщений
# @router.message()
# async def process_other_messages(message: Message):

#     await message.answer(
#         "Я понимаю только команды. Используйте /help, "
#         "чтобы увидеть список доступных команд или нажмите на шапку бота."
#     )
