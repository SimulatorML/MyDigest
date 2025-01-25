from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.data.database import (
    fetch_user_channels,
    add_user,
    add_user_channels,
    delete_user_channels,
    clear_user_channels,
)


router = Router()


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
        "/delete - удалить каналы\n"
        "/clear - полностью очистить список каналов\n"
        "/help - показать эту справку"
    )


@router.message(Command(commands="help"))
async def process_help_command(message: Message):
    await message.answer(
        "Я помогу вам создавать дайджесты из выбранных Telegram каналов.\n\n"
        "Доступные команды:\n"
        "/add_channels - добавить каналы\n"
        "/show_channels - показать список ваших каналов\n"
        "/delete - удалить каналы\n"
        "/clear - полностью очистить список каналов\n"
        "/help - показать эту справку"
    )


@router.message(Command(commands="add_channels"))
async def process_add_channels_command(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "unknown"

    # Добавляем или обновляем пользователя
    await add_user(user_id, username)

    await message.answer(
        "Пожалуйста, отправьте список каналов в формате: @channel1 @channel2"
    )
    # Устанавливаем состояние ожидания ввода каналов
    await state.set_state(UserStates.waiting_for_channels)


# Обработчик для получения списка каналов
@router.message(UserStates.waiting_for_channels)
async def process_channels_input(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    channels_text = message.text.strip()

    if not channels_text:
        await message.answer("Пожалуйста, отправьте корректный список каналов.")
        return

    # Разбиваем текст на отдельные каналы
    new_channels = [ch.strip() for ch in channels_text.split() if ch.strip()]

    if not all(ch.startswith("@") for ch in new_channels):
        await message.answer("Все каналы должны начинаться с '@'")
        return

    result = await add_user_channels(user_id, new_channels)

    if result is not None:
        await message.answer(f"Каналы добавлены: {', '.join(new_channels)}")
    else:
        await message.answer("Произошла ошибка при добавлении каналов.")

    # Сбрасываем состояние
    await state.clear()


@router.message(Command(commands="show_channels"))
async def process_show_channels_command(message: Message):
    user_id = str(message.from_user.id)
    channels = await fetch_user_channels(user_id)

    if channels:
        channel_names = [channel["channel_name"] for channel in channels]
        await message.answer(f"Ваши каналы:\n{', '.join(channel_names)}")
    else:
        await message.answer("У вас пока нет добавленных каналов.")


@router.message(Command(commands="delete"))
async def process_delete_command(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    channels = await fetch_user_channels(user_id)

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
    user_id = str(message.from_user.id)
    channels_to_delete = [ch.strip() for ch in message.text.split() if ch.strip()]

    # Проверяем формат каналов
    if not all(ch.startswith("@") for ch in channels_to_delete):
        await message.answer("Все каналы должны начинаться с '@'. Попробуйте снова.")
        return

    await delete_user_channels(user_id, channels_to_delete)
    await message.answer(f"Каналы удалены: {', '.join(channels_to_delete)}")
    await state.clear()


@router.message(Command(commands="clear"))
async def process_clear_command(message: Message):
    user_id = str(message.from_user.id)
    await clear_user_channels(user_id)
    await message.answer("Все каналы удалены.")


@router.callback_query(lambda c: c.data.startswith("clear_"))
async def process_clear_callback(callback: CallbackQuery):
    user_id = str(callback.from_user.id)

    if callback.data == "clear_confirm":
        await clear_user_channels(user_id)  # Очищаем каналы в Supabase
        await callback.message.edit_text("✅ Список каналов успешно очищен.")
    else:  # clear_cancel
        await callback.message.edit_text("❌ Очистка списка каналов отменена.")

    await callback.answer()


# Хэндлер для всех остальных сообщений
@router.message()
async def process_other_messages(message: Message):
    await message.answer(
        "Я понимаю только команды. Используйте /help, "
        "чтобы увидеть список доступных команд."
    )
