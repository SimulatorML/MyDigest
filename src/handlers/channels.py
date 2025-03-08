import asyncio
import re
import logging
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram import F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
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
        "Привет 🙂 Я бот для создания дайджестов из Telegram каналов и чатов.\n\n"
        "1️⃣Сначала добавьте каналы:"
        "       способ 1: просто перешлите сюда пост из канала\n"
        "       способ 2: нажмите на /add_channels, затем вставьте список каналов\n"
        "2️⃣Нажмите на /receive_news, чтобы сводки новостей приходили каждый час.\n"
        "3️⃣Если хотите также получать сводку по чату, то его можно добавить только через /add_channels.\n\n"
        "Каналов и чатов можно добавлять сколько угодно и когда угодно ❤️\n\n"
        "👇Вот список всех команды:\n"
        "/add_channels - добавить каналы\n"
        "/show_channels - показать список ваших каналов\n"
        "/delete_channels - удалить каналы\n"
        "/clear_channels - полностью очистить список каналов\n"
        "/help - показать список команд\n"
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
        f"Жду список каналов 👀\n\n"
        f"Формат может быть произвольным.\n"
        f"Например: @channel1 https://t.me/channel2 channel3\n\n"
        f"Если передумали - нажмите 👉 /cancel"
    )
    # Устанавливаем состояние ожидания ввода каналов
    await state.set_state(UserStates.waiting_for_channels)

### Обработчик для получения списка каналов
@router.message(UserStates.waiting_for_channels)
async def process_channels_input(message: Message, state: FSMContext):

    # Если это пересылка поста из группы, то добавляем как forwarded сообщение
    if message.forward_from_chat and message.forward_from_chat.type == 'channel':
        await forwarded_message(message)
        return

    # Если это пересылка от юзера в чате, то пишем что это человек
    if message.from_user and not message.text.startswith('/'):
        await message.answer("❌Кажется, вы переслали сообщение от человека 🧍, а не пост из группы.\n\n"
                             "Перешлите пост из канала)\n\n"
                             "А если вы хотите добавить чат канала, то нажмите 👉 /add_channels, а затем вставьте ссылку на чат канала")
        return

    # Сбрасываем состояние если сообщение - команда
    if message.text and message.text.startswith('/cancel'):
        await message.answer(f"Вы отменили добавление каналов 👌")
        await state.clear()
        return

    # Получаем данные из сообщения
    user_id = message.from_user.id
    channels_text = message.text.strip()
    addition_timestamp = datetime.now().isoformat()

    if not channels_text:
        await message.answer("Пожалуйста, отправьте корректный список каналов.")
        return

    # Обрабатываем список каналов
    new_channels = process_channel_list(channels_text)

    if not new_channels:
        await message.answer("Не удалось распознать ни одного корректного канала. Пожалуйста, попробуйте снова.")
        return

    try:
        success = await db.add_user_channels(user_id, list(new_channels), addition_timestamp)
        if success:
            channels_list = ', '.join(new_channels)
            await message.answer(f"Каналы успешно добавлены 👍\n{channels_list}")
        else:
            await message.answer("Произошла ошибка при добавлении каналов. Попробуйте еще раз.")
    except Exception as e:
        logging.error(f"Error adding channels for user {user_id}: {str(e)}")
        await message.answer("Произошла ошибка при добавлении каналов. Попробуйте позже.")
    finally:
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

    # Проверяем, есть ли у пользователя добавленные каналы
    if not channels:
        await message.answer("У вас нет добавленных каналов для удаления.")
        return

    channel_names = [channel["channel_name"] for channel in channels]
    await message.answer(
        f"Текущий список ваших каналов:\n"
        f"{', '.join(channel_names)}\n\n"
        f"Введите канал или список каналов для удаления\n\n"
        f"Если передумали - нажмите 👉 /cancel"
    )

    # Активируем состояние ожидания ввода каналов
    await state.set_state(UserStates.waiting_for_delete)

## Состояние ожидания ввода каналов для удаления
@router.message(UserStates.waiting_for_delete)
async def process_delete_channels(message: Message, state: FSMContext):
    # Сбрасываем состояние если сообщение - другая команда
    if message.text.startswith('/'):
        await message.answer(f"Вы отменили удаление 👌")
        await state.clear()
        return

    user_id = message.from_user.id

    # Обрабатываем список каналов
    channels_to_delete = process_channel_list(message.text)

    if not channels_to_delete:
        await message.answer("Не удалось распознать ни одного канала. Пожалуйста, попробуйте снова.")
        return

    if not all(re.match(r"^@[A-Za-z0-9_]+$", ch) for ch in channels_to_delete):
        await message.answer(
            "Названия каналов могут содержать только латинские буквы, цифры и знак подчеркивания. "
            "Пожалуйста, проверьте правильность написания и попробуйте снова."
        )
        return

    result = await db.delete_user_channels(user_id, list(channels_to_delete))
    if not result:
        await message.answer("Произошла ошибка при удалении каналов\nили неверно введены данные.")
        return

    await message.answer(f"Каналы удалены: {', '.join(channels_to_delete)}")
    # Сбрасываем состояние
    await state.clear()

############################## clear_channels - Очистить каналы #################

@router.message(Command(commands="clear_channels"))
async def process_clear_command(message: Message):
    # Создаем объекты инлайн-кнопок
    confirm_button = InlineKeyboardButton(
        text='✅ Да, очистить',
        callback_data='confirm_clear'
    )
    cancel_button = InlineKeyboardButton(
        text='❌ Отмена',
        callback_data='cancel_clear'
    )
    
    # Добавляем кнопки в клавиатуру в один ряд
    keyboard: list[list[InlineKeyboardButton]] = [
        [confirm_button, cancel_button]
    ]
    
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        text='⚠️Вы уверены, что хотите удалить ВСЕ каналы?\n'
             'Это действие необратимо.',
        reply_markup=markup
    )

# Если пользователь подтвердил удаление
@router.callback_query(F.data == "confirm_clear")
async def process_clear_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    result = await db.clear_user_channels(user_id)
    if result:
        await callback.message.edit_text(
            "✅ Все каналы успешно удалены."
        )
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при очистке каналов."
        )

# если пользователь отменил удаление
@router.callback_query(F.data == "cancel_clear")
async def process_clear_cancel(callback: CallbackQuery):
    await callback.message.edit_text(
        "Операция отменена. Ваши каналы остались без изменений."
    )

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
        logging.error("Error in receive_news_handler: %s", e)

##############################  FORWARD: Добавить канал через пересылку #################

@router.message(lambda message: message.forward_from_chat and message.forward_from_chat.type == 'channel')
async def handle_forwarded_message(message: Message):
    await forwarded_message(message)

# Функция для обработки пересылки
async def forwarded_message(message: Message):
    
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

############################## Перехват обычного текста #############################

# Для всех остальных сообщений
@router.message()
async def process_other_messages(message: Message):
    # Если без причины нажать на /cancel
    if message.text == "/cancel":
        await message.answer("Нечего отменять 🤷‍♂️")
        return

    if message.forward_from:
        await message.answer("❌Кажется, вы переслали сообщение от человека 🧍, а не пост из группы.\n\n"
                             "Перешлите пост из канала)\n\n"
                             "А если вы хотите добавить чат канала, то нажмите 👉 /add_channels, а затем вставьте ссылку на чат канала")
        return
    
        # Если юзер сел попой на телефон
    if  message.text and not message.text.startswith('/'):
        # Если неизвестная команды или текст или пересылка из лички
        await message.answer(
            "Я понимаю только команды. Используйте /help, "
            "чтобы увидеть список доступных команд или нажмите на Меню."
        )
        return


############################## Функция обработки списка каналов #############################
def process_channel_list(channels_text: str) -> set[str]:
    """
    Обрабатывает список каналов из текста и возвращает множество корректных имен каналов.
    
    Args:
        channels_text (str): Текст со списком каналов
        
    Returns:
        set[str]: Множество обработанных имен каналов
    """
    # Разделяем по пробелам и запятым
    raw_channels = re.split(r'[,\s]+', channels_text)
    
    # Обрабатываем каждый канал
    processed_channels = set()
    for channel in raw_channels:
        try:
            # Очищаем от пробелов
            channel = channel.strip()
            if not channel:
                continue
                
            # Извлекаем имя канала из URL
            channel_name = channel.split('/')[-1].strip()
            
            # Убираем все лишние символы
            channel_name = re.sub(r'[^\w]', '', channel_name)
            
            # Добавляем @ в начало
            if not channel_name.startswith('@'):
                channel_name = f'@{channel_name}'
                
            processed_channels.add(channel_name)
        except Exception as e:
            logging.error(f"Error processing channel {channel}: {str(e)}")
            continue
            
    return processed_channels
