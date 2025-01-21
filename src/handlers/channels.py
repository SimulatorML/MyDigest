import json
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from definitions import CHANNELS_FILE

router = Router()

class UserStates(StatesGroup):
    waiting_for_channels = State()
    waiting_for_delete = State()

def load_user_channels():
    try:
        with open(CHANNELS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_user_channels(data):
    CHANNELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHANNELS_FILE, 'w') as file:
        json.dump(data, file, indent=4)

@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(
        'Привет! Я бот для создания дайджестов из Telegram каналов.\n'
        'Используйте следующие команды:\n'
        '/add_channels - добавить каналы\n'
        '/show_channels - показать список ваших каналов\n'
        '/delete - удалить каналы\n'
        '/clear - полностью очистить список каналов\n'
        '/help - показать эту справку'
    )

@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(
        'Я помогу вам создавать дайджесты из выбранных Telegram каналов.\n\n'
        'Доступные команды:\n'
        '/add_channels - добавить каналы\n'
        '/show_channels - показать список ваших каналов\n'
        '/delete - удалить каналы\n'
        '/clear - полностью очистить список каналов\n'
        '/help - показать эту справку'
    )

@router.message(Command(commands='add_channels'))
async def process_add_channels_command(message: Message, state: FSMContext):
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
    
    if not all(ch.startswith('@') for ch in new_channels):
        await message.answer("Все каналы должны начинаться с '@'")
        return

    # Загружаем существующие данные
    user_data = load_user_channels()
    
    # Получаем текущие каналы пользователя или создаем пустой список
    current_channels = user_data.get(user_id, [])
    
    # Добавляем новые каналы, избегая дублирования
    updated_channels = list(set(current_channels + new_channels))
    
    # Обновляем список каналов пользователя
    user_data[user_id] = updated_channels
    
    # Сохраняем обновленные данные
    save_user_channels(user_data)
    
    # Формируем сообщение о добавленных каналах
    new_added = [ch for ch in new_channels if ch not in current_channels]
    already_existing = [ch for ch in new_channels if ch in current_channels]
    
    response = "Обновление списка каналов:\n"
    if new_added:
        response += f"✅ Добавлены новые каналы: {', '.join(new_added)}\n"
    if already_existing:
        response += f"ℹ️ Уже были в списке: {', '.join(already_existing)}\n"
    response += f"\nТекущий список всех каналов:\n{', '.join(updated_channels)}"
    
    await message.answer(response)
    # Сбрасываем состояние
    await state.clear()

@router.message(Command(commands='show_channels'))
async def process_show_channels_command(message: Message):
    user_id = str(message.from_user.id)
    user_data = load_user_channels()
    
    if user_id in user_data:
        channels = user_data[user_id]
        await message.answer(
            f"Ваши каналы:\n{', '.join(channels)}"
        )
    else:
        await message.answer(
            "У вас пока нет добавленных каналов.\n"
            "Используйте /add_channels для добавления."
        )

@router.message(Command(commands='delete'))
async def process_delete_command(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_data = load_user_channels()
    
    if user_id not in user_data or not user_data[user_id]:
        await message.answer("У вас нет добавленных каналов для удаления.")
        return
    
    current_channels = user_data[user_id]
    await message.answer(
        f"Текущий список ваших каналов:\n"
        f"{', '.join(current_channels)}\n\n"
        f"Введите канал или список каналов для удаления (например: @channel1 @channel2)"
    )
    await state.set_state(UserStates.waiting_for_delete)

@router.message(UserStates.waiting_for_delete)
async def process_delete_channels(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    channels_to_delete = [ch.strip() for ch in message.text.split() if ch.strip()]
    
    # Проверяем формат каналов
    if not all(ch.startswith('@') for ch in channels_to_delete):
        await message.answer("Все каналы должны начинаться с '@'. Попробуйте снова.")
        return
    
    # Загружаем текущие данные
    user_data = load_user_channels()
    if user_id not in user_data:
        await message.answer("У вас нет добавленных каналов.")
        await state.clear()
        return
    
    current_channels = user_data[user_id]
    
    # Находим каналы, которые можно удалить и которых нет в списке
    deleted_channels = []
    not_found_channels = []
    
    for channel in channels_to_delete:
        if channel in current_channels:
            current_channels.remove(channel)
            deleted_channels.append(channel)
        else:
            not_found_channels.append(channel)
    
    # Обновляем список каналов
    user_data[user_id] = current_channels
    save_user_channels(user_data)
    
    # Формируем ответное сообщение
    response = []
    if deleted_channels:
        response.append(f"✅ Удалены каналы: {', '.join(deleted_channels)}")
    if not_found_channels:
        response.append(f"❌ Не найдены каналы: {', '.join(not_found_channels)}")
    response.append(f"\nТекущий список каналов:\n{', '.join(current_channels) if current_channels else 'Список пуст'}")
    
    await message.answer("\n".join(response))
    await state.clear()

@router.message(Command(commands='clear'))
async def process_clear_command(message: Message):
    user_id = str(message.from_user.id)
    user_data = load_user_channels()
    
    if user_id not in user_data or not user_data[user_id]:
        await message.answer("У вас нет добавленных каналов для очистки.")
        return
    
    # Показываем текущие каналы и запрашиваем подтверждение
    current_channels = user_data[user_id]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, очистить", callback_data="clear_confirm"),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data="clear_cancel")
        ]
    ])
    
    await message.answer(
        f"Вы уверены, что хотите удалить ВСЕ каналы из списка?\n\n"
        f"Текущие каналы:\n{', '.join(current_channels)}",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith('clear_'))
async def process_clear_callback(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if callback.data == "clear_confirm":
        user_data = load_user_channels()
        if user_id in user_data:
            user_data[user_id] = []  # Очищаем список каналов
            save_user_channels(user_data)
            await callback.message.edit_text("✅ Список каналов успешно очищен.")
        else:
            await callback.message.edit_text("Список каналов уже пуст.")
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