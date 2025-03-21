import asyncio
import re
import logging
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram import F
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.scraper import TelegramScraper
from src.data.database import supabase
from src.data.database import SupabaseDB
from src.scraper import init_telethon_client
from src.config import NEWS_CHECK_INTERVAL, DAY_RANGE_INTERVAL, MISTRAL_KEY
from src.summarization import Summarization
import src.handlers.keyboards as kb

router = Router()
db = SupabaseDB(supabase)
summarizer = Summarization(api_key=MISTRAL_KEY)

class UserStates(StatesGroup):
    waiting_for_channels = State()
    waiting_for_delete = State()
    selecting_channels = State()


############################## Приветствие и тъюториал ###############################

TUTORIAL_STEPS = [
    (

'''Привет! 🙂 Я бот для создания сводок новостей из Telegram каналов и чатов.

<b>Для начала добавьте каналы одним из двух способов:</b>

1️⃣ Просто перешлите сюда пост из канала.  
2️⃣ Или пришлите ссылку на канал или его название в любом формате. 

Например:  
@channel1 https://t.me/channel2 channel3

Отметим, что отправлять посты или ссылки на каналы можно в любое время.
        '''.strip()
    ),
    (

'''Нажмите на кнопку <b>Получать новости</b>, чтобы сводки новостей приходили каждый час.

После нажатия кнопки в течение 5 минут вам придет первый дайджест. Следующий дайджест придет ровно через час.

Для того чтобы остановить получение новостных сводок, можно нажать на кнопку <b>Остановить новости</b>. Чтобы заново получать новости, достаточно лишь повторного нажатия на кнопку <b>Получать новости</b>.
        '''.strip()
    ),
    (
        '''
<b>Если хотите получать сводку по чату</b>, то его можно добавить только через кнопку <b>Добавить каналы</b>.

Каналов и чатов можно добавлять сколько угодно и когда угодно ❤️
        '''.strip()
    ),
    (
        '''
Вот список всех команд:

    /add_channels - добавить каналы
    /show_channels - показать список ваших каналов
    /delete_channels - удалить каналы
    /help - показать список команд
    /receive_news - показывать сводки новостей за час

Нажмите «Назад», чтобы вернуться к предыдущему шагу или «Завершить», чтобы закончить.
        '''.strip()
    )
]

@router.message(CommandStart())
async def process_start_command(message: Message):

    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "unknown"
    login_timestamp = datetime.now().isoformat()

    user_exists = await db.fetch_user(user_id)
    if not user_exists:
        await db.add_user(user_id, username, login_timestamp)


    # 2) Prepare the first tutorial screen
    step_index = 0
    total_steps = len(TUTORIAL_STEPS)

    text = TUTORIAL_STEPS[step_index]
    keyboard = get_tutorial_keyboard(step_index, total_steps)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("Вот главное меню:", reply_markup=kb.menu)


def get_tutorial_keyboard(step_index: int, total_steps: int) -> InlineKeyboardMarkup:
    """
    Inline keyboard helper: returns 'Back' + 'Next' or 'Finish' buttons, depending on the step.
    """
    buttons = []

    # Show '← Назад' if not on the first screen
    if step_index > 0:
        buttons.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"tutorial_back_{step_index}"
            )
        )

    # Show 'Далее →' if not on the last screen
    if step_index < total_steps - 1:
        buttons.append(
            InlineKeyboardButton(
                text="Далее →",
                callback_data=f"tutorial_next_{step_index}"
            )
        )
    else:
        # On the last screen, show 'Завершить'
        buttons.append(
            InlineKeyboardButton(
                text="Завершить",
                callback_data="tutorial_finish"
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


# ---------- TUTORIAL NAVIGATION CALLBACKS ----------

@router.callback_query(lambda c: c.data and c.data.startswith("tutorial_next_"))
async def tutorial_next_handler(callback: CallbackQuery):
    await callback.answer()

    data = callback.data  # e.g. "tutorial_next_0"
    current_step = int(data.split("_")[-1])
    next_step = current_step + 1

    total_steps = len(TUTORIAL_STEPS)
    if next_step < total_steps:
        new_text = TUTORIAL_STEPS[next_step]
        new_kb = get_tutorial_keyboard(next_step, total_steps)
        await callback.message.edit_text(new_text, reply_markup=new_kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data and c.data.startswith("tutorial_back_"))
async def tutorial_back_handler(callback: CallbackQuery):
    await callback.answer()

    data = callback.data  # e.g. "tutorial_back_2"
    current_step = int(data.split("_")[-1])
    prev_step = current_step - 1

    if prev_step >= 0:
        new_text = TUTORIAL_STEPS[prev_step]
        new_kb = get_tutorial_keyboard(prev_step, len(TUTORIAL_STEPS))
        await callback.message.edit_text(new_text, reply_markup=new_kb, parse_mode="HTML")


# ---------- 6) Handle "Finish" button ----------

@router.callback_query(lambda c: c.data and c.data == "tutorial_finish")
async def tutorial_finish_handler(callback: CallbackQuery):
    """
    Handles the 'Finish' button on the last step.
    """
    await callback.answer()
    await callback.message.edit_text(
        "Обучение завершено! Теперь вы можете использовать команды бота."
    )


############################## help - Показать справку #############################
@router.message(Command(commands="help"))
async def process_help_command(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/add_channels - добавить каналы\n"
        "/show_channels - показать список ваших каналов\n"
        "/delete_channels - удалить каналы\n"
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
        await state.clear()
        return

    # Сбрасываем состояние если сообщение - команда
    if message.text and message.text.startswith('/'):
        await message.answer("Вы отменили добавление каналов 👌")
        await state.clear()
        return

    # Если это пересылка от юзера в чате, то пишем что это человек
    if message.forward_from and message.from_user:
        await message.answer("❌Кажется, вы переслали сообщение от человека 🧍, а не пост из группы.\n\n"
                             "Перешлите пост из канала)\n\n"
                             "А если вы хотите добавить чат канала, то нажмите 👉 /add_channels, а затем вставьте ссылку на чат канала")
        await state.clear()
        return

    user_id = message.from_user.id
    channels_text = message.text.strip()
    addition_timestamp = datetime.now().isoformat()
    scraper = TelegramScraper(user_id)

    if not channels_text:
        await message.answer("Пожалуйста, отправьте корректный список каналов.")
        return

    # Обрабатываем список каналов
    new_channels = process_channel_list(channels_text)

    if not new_channels:
        await message.answer("Не удалось распознать ни одного корректного канала. Пожалуйста, попробуйте снова.")
        return

    if not all(re.match(r"^@[A-Za-z0-9_]+$", ch) for ch in new_channels):
        await message.answer(
            "Названия каналов могут содержать только латинские буквы, цифры и знак подчеркивания. "
            "Пожалуйста, проверьте правильность написания и попробуйте снова."
        )
        return

    try:
        tasks = [
            asyncio.create_task(
                summarizer.determine_channel_topic(
                    await scraper.scrape_messages_long_term(channel, days=DAY_RANGE_INTERVAL, limit=10)
                )
            )
            for channel in new_channels
        ]

        # Ожидаем завершения всех задач
        channel_topics = await asyncio.gather(*tasks)
        # logging.info("\n\nСписок тем каналов для сохранения в БД: %s\n", channel_topics)

        success = await db.add_user_channels(user_id, list(new_channels), addition_timestamp, channel_topics)
        if success:
            channels_list = ', '.join(new_channels)
            await message.answer(f"Каналы успешно добавлены 👍\n{channels_list}")
        else:
            await message.answer("Произошла ошибка при добавлении каналов. Попробуйте еще раз.")
    except Exception as e:
        logging.error("\nError adding channels for user %s: %s\n", user_id, e)
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
    # Сбрасываем состояние, если есть активное
    await state.clear()

    user_id = message.from_user.id
    channels = await db.fetch_user_channels(user_id)

    if not channels:
        await message.answer("У вас нет добавленных каналов.")
        return

    # Сохраняем список каналов в состоянии
    await state.update_data(channels=[channel["channel_name"] for channel in channels])
    await state.set_state(UserStates.selecting_channels)

    # Создаем билдер для inline-клавиатуры
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки каналов
    for channel in channels:
        channel_name = channel["channel_name"]
        builder.button(text=channel_name, callback_data=f"select_{channel_name}")

    # Распределяем кнопки каналов по строкам (по 2 кнопки в строке)
    builder.adjust(2)

    # Добавляем кнопки действий в отдельные строки
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_delete"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить все каналы", callback_data="delete_all")
    )

    # Отправляем сообщение с клавиатурой
    await message.answer(
        "Выберите каналы для удаления (нажмите на канал, чтобы отметить его):",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith('select_'), UserStates.selecting_channels)
async def process_select_callback(callback: CallbackQuery, state: FSMContext):
    channel_name = callback.data[len('select_'):]  # Извлекаем имя канала из callback_data

    # Получаем текущие данные из состояния
    data = await state.get_data()
    selected_channels = data.get("selected_channels", [])
    channels = data.get("channels", [])

    # Если канал уже выбран, убираем его из списка, иначе добавляем
    if channel_name in selected_channels:
        selected_channels.remove(channel_name)
    else:
        selected_channels.append(channel_name)

    # Обновляем состояние
    await state.update_data(selected_channels=selected_channels)

    # Создаем билдер для inline-клавиатуры
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки каналов
    for channel in channels:
        text = f"📌 {channel}" if channel in selected_channels else channel
        builder.button(text=text, callback_data=f"select_{channel}")

    # Распределяем кнопки каналов по строкам (по 2 кнопки в строке)
    builder.adjust(2)

    # Добавляем кнопки действий в отдельные строки
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_delete"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить все каналы", callback_data="delete_all")  # Добавляем кнопку "Удалить все каналы"
    )

    # Обновляем сообщение с новой клавиатурой
    await callback.message.edit_text(
        "Выберите каналы для удаления (нажмите на канал, чтобы отметить его):",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Когда пользователь нажимает "Подтвердить", удаляем выбранные каналы.
@router.callback_query(F.data == "confirm_delete", UserStates.selecting_channels)
async def process_confirm_delete_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    # Получаем выбранные каналы из состояния
    data = await state.get_data()
    selected_channels = data.get("selected_channels", [])

    if not selected_channels:
        await callback.answer("Вы не выбрали ни одного канала.")
        return

    # Удаляем выбранные каналы из базы данных
    result = await db.delete_user_channels(user_id, selected_channels)
    
    if result:
        await callback.message.edit_text(f"Каналы успешно удалены: {', '.join(selected_channels)}")
    else:
        await callback.message.edit_text("Произошла ошибка при удалении каналов.")

    # Сбрасываем состояние
    await state.clear()

# Если пользователь нажимает "Отмена", просто сбрасываем состояние.
@router.callback_query(F.data == "cancel_delete", UserStates.selecting_channels)
async def process_cancel_delete_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Операция удаления отменена.")
    await state.clear()

@router.callback_query(F.data == "cancel")
async def process_cancel_callback(callback: CallbackQuery):
    await callback.message.edit_text("Операция удаления отменена.")
    await callback.message.edit_reply_markup(reply_markup=None)

## Удалить все каналы
@router.callback_query(F.data == "delete_all", UserStates.selecting_channels)
async def process_delete_all_callback(callback: CallbackQuery, state: FSMContext):
    # Создаем клавиатуру для подтверждения удаления
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить все", callback_data="confirm_delete_all"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_all")
    )

    # Отправляем сообщение с запросом подтверждения
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите удалить ВСЕ каналы? Это действие необратимо.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_delete_all", UserStates.selecting_channels)
async def process_confirm_delete_all_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    # Удаляем все каналы из базы данных
    result = await db.clear_user_channels(user_id)
    
    if result:
        await callback.message.edit_text("✅ Все каналы успешно удалены.")
    else:
        await callback.message.edit_text("❌ Произошла ошибка при удалении каналов.")

    # Сбрасываем состояние
    await state.clear()

@router.callback_query(F.data == "cancel_delete_all", UserStates.selecting_channels)
async def process_cancel_delete_all_callback(callback: CallbackQuery, state: FSMContext):
    # Возвращаем пользователя к выбору каналов
    data = await state.get_data()
    channels = data.get("channels", [])

    # Создаем билдер для inline-клавиатуры
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки каналов
    for channel in channels:
        channel_name = channel
        builder.button(text=channel_name, callback_data=f"select_{channel_name}")

    # Распределяем кнопки каналов по строкам (по 2 кнопки в строке)
    builder.adjust(2)

    # Добавляем кнопки действий в отдельные строки
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_delete"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить все каналы", callback_data="delete_all")
    )

    # Обновляем сообщение с клавиатурой
    await callback.message.edit_text(
        "Выберите каналы для удаления (нажмите на канал, чтобы отметить его):",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


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

############################## receive_news - Получить сводки новостей ############

@router.message(Command("receive_news"))
async def receive_news_handler(message: Message, state: FSMContext):

    # Сбрасываем состояние, если есть активное
    await state.clear()

    user_id = message.from_user.id
    #Marking the user in the db who is CURRENTLY using the bot
    await db.set_user_receiving_news(user_id, True)
    scraper = TelegramScraper(user_id)

    try:
        # Инициализируем клиент только при первом запросе
        await init_telethon_client()

        if scraper.stop_auto_news_check(user_id):
            await message.answer("🔄 Перезапускаю фоновую проверку новостей...")

        task = asyncio.create_task(scraper.start_auto_news_check(user_id, interval=NEWS_CHECK_INTERVAL))
        TelegramScraper.running_tasks[user_id] = task

        await message.answer(
            f"✅ Фоновая проверка новостей запущена. "
            f"Вы будете получать обновления каждые {NEWS_CHECK_INTERVAL // 60} минут."
        )
    except Exception as e:
        await message.answer("❌ Произошла ошибка при запуске проверки новостей. Попробуйте позже.")
        logging.error("Error in receive_news_handler: %s", e)

@router.message(F.text == "Получать новости")
async def handle_receive_news_btn(message: Message):
    # Reuse /receive_news logic:
    await receive_news_handler(message)

############################## stop_news Остановить получение сводки новостей #################
@router.message(Command("stop_news"))
async def stop_news_handler(message: Message, state: FSMContext):
    # Сбрасываем состояние, если есть активное
    await state.clear()

    user_id = message.from_user.id
    scraper = TelegramScraper(user_id)
    await db.set_user_receiving_news(user_id, False)
    scraper.stop_auto_news_check(user_id)
    await message.answer(
        "Вы остановили получение новостей. "
        "Для повторного получения новостей, пожалуйста, вызовите /receive_news"
    )

@router.message(F.text == "Остановить новости")
async def handle_stop_news_btn(message: Message):
    # Reuse /stop_news logic:
    await stop_news_handler(message)

##############################  FORWARD: Добавить канал через пересылку #################

@router.message(F.forward_from_chat.func(lambda chat: chat and chat.type == 'channel'))
async def handle_forwarded_message(message: Message, state: FSMContext):
    # Сбрасываем состояние, если есть активное
    await state.clear()
    
    if message.media_group_id:
        data = await state.get_data()
        processed_groups = data.get("processed_media_groups", set())

        if message.media_group_id in processed_groups:
            await message.delete()
            return
        else:
            processed_groups.add(message.media_group_id)
            await state.update_data(processed_media_groups=processed_groups)
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
    channels = await db.fetch_user_channels(user_id)
    channels_names = ', '.join([channel["channel_name"] for channel in channels])

    if success:
        await message.answer(f"Канал {channel} успешно добавлен! ✔️ \nОбновленный список каналов: {channels_names}")
        await message.delete()
    else:
        await message.answer("Произошла ошибка при добавлении канала. Пожалуйста, попробуйте позже.")
        await message.delete()
        return

############################## Перехват обычного текста #############################

# Для всех остальных сообщений
@router.message()
async def process_other_messages(message: Message, state: FSMContext):
    # Сбрасываем состояние, если есть активное
    await state.clear()

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


## Обработчик для получения списка каналов
@router.message(lambda message: message.text and not message.text.startswith('/'))
async def process_channels_input(message: Message):

    # Если это пересылка поста из группы, то добавляем как forwarded сообщение
    if message.forward_from_chat and message.forward_from_chat.type == 'channel':
        await forwarded_message(message)
        return

    # Если это пересылка от юзера в чате, то пишем что это человек
    if message.forward_from and message.from_user:
        await message.answer("❌Кажется, вы переслали сообщение от человека 🧍, а не пост из группы.\n\n"
                             "Перешлите пост из канала)\n\n"
                             "А если вы хотите добавить чат канала, то нажмите 👉 /add_channels, а затем вставьте ссылку на чат канала")
        return

    user_id = message.from_user.id
    channels_text = message.text.strip()
    addition_timestamp = datetime.now().isoformat()
    scraper = TelegramScraper(user_id)

    # Обрабатываем список каналов
    new_channels = process_channel_list(channels_text)
    if not new_channels:
        await message.answer("Не удалось распознать ни одного корректного канала. Пожалуйста, попробуйте снова.")
        return

    if not all(re.match(r"^@[A-Za-z0-9_]+$", ch) for ch in new_channels):
        await message.answer(
            "Названия каналов могут содержать только латинские буквы, цифры и знак подчеркивания. "
            "Пожалуйста, проверьте правильность написания и попробуйте снова."
        )
        return

    try:
        tasks = [
            asyncio.create_task(
                summarizer.determine_channel_topic(
                    await scraper.scrape_messages_long_term(channel, days=DAY_RANGE_INTERVAL, limit=10)
                )
            )
            for channel in new_channels
        ]

        # Ожидаем завершения всех задач
        channel_topics = await asyncio.gather(*tasks)
        # logging.info("\n\nСписок тем каналов для сохранения в БД: %s\n", channel_topics)


        channels = await db.fetch_user_channels(user_id)
        channels_names = ', '.join([channel["channel_name"] for channel in channels])

        success = await db.add_user_channels(user_id, list(new_channels), addition_timestamp, channel_topics)
        if success:
            channels_list = ', '.join(new_channels)
            await message.answer(f"Каналы успешно добавлены 👍\n{channels_list}. Обновленный список каналов: {channels_names}")
        else:
            await message.answer("Произошла ошибка при добавлении каналов. Попробуйте еще раз.")
    except Exception as e:
        logging.error("\nError adding channels for user %s: %s\n", user_id, e)
        await message.answer("Произошла ошибка при добавлении каналов. Попробуйте позже.")
