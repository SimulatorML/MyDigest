import asyncio
import re
import logging
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram import F
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.scraper import TelegramScraper
from src.data.database import supabase
from src.data.database import SupabaseDB
from src.scraper import init_telethon_client
from src.config import MISTRAL_KEY
from src.summarization import Summarization
import src.handlers.keyboards as kb

router = Router()
db = SupabaseDB(supabase)
summarizer = Summarization(api_key=MISTRAL_KEY)

class UserStates(StatesGroup):
    waiting_for_channels = State()
    waiting_for_delete = State()
    selecting_channels = State()
    waiting_for_interval = State()


############################## Приветствие и тъюториал ###############################

TUTORIAL_STEPS = [
    (

'''Привет! 🙂 Я бот для создания сводок новостей из Telegram каналов и чатов.

<b>Для начала добавьте каналы одним из двух способов:</b>

1️⃣ Просто перешлите сюда пост из канала.  
2️⃣ Или пришлите ссылку на канал или его название в любом формате. 

Например:  
@channel1 https://t.me/channel2 channel3
        '''.strip()
    ),
    (

'''Нажмите на кнопку <b>Получать новости</b>, тогда в течение 5 минут вам придет первый дайджест.

По умолчанию, новости собираются за 1 предыдущий час, но вы можете поменять интервал, нажав на /set_interval.

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

    /set_interval    - ⏲️ установить интервал
    /delete_channels - 🗑️ удалить каналы
    /receive_news    - 📰 показывать сводки новостей
    /stop_news       - ⛔️ остановить сводку новостей
    /show_channels   - 📋 показать список ваших каналов

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
        await db.add_user(user_id, username, login_timestamp, check_interval=3600)


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
@router.message(F.text == "Помощь")
async def handle_help_btn(message: Message):
    # Reuse /stop_news logic:
    await process_help_command(message)

@router.message(Command(commands="help"))
async def process_help_command(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/set_interval    - ⏲️ установить интервал\n"
        "/delete_channels - 🗑️ удалить каналы\n"
        "/receive_news    - 📰 показывать сводки новостей\n"
        "/stop_news       - ⛔️ остановить сводку новостей\n"
        "/show_channels   - 📋 показать список ваших каналов\n"
    )

############################## set_interval - интервал для получения дайджестов  #####################

### Функция для перезапуска дайджеста
async def _restart_news_check(user_id: int, interval_sec: int, message: Message):
    """Перезапускает задачу проверки новостей с новым интервалом."""
    scraper = TelegramScraper(user_id)
    try:
        # Останавливаем текущую задачу, если она есть
        if user_id in TelegramScraper.running_tasks:
            TelegramScraper.running_tasks[user_id].cancel()
            del TelegramScraper.running_tasks[user_id]
            await message.answer("🔄 Перезапускаю фоновую проверку...")

        # Создаем новую задачу с актуальным интервалом
        task = asyncio.create_task(scraper.start_auto_news_check(user_id, interval=interval_sec))
        TelegramScraper.running_tasks[user_id] = task
        await message.answer(f"✅ Проверка новостей запущена. Интервал: {interval_sec // 60} мин.")

    except Exception as e:
        await message.answer("❌ Ошибка при перезапуске. Попробуйте позже.")
        logging.error("Ошибка в _restart_news_check: %s", e)

### Устанавливаем интервал
@router.message(Command("set_interval"))
async def set_interval_handler(message: Message, command: CommandObject, state: FSMContext):
    args = command.args
    if not args:
        await message.answer("📝 Введите интервал в минутах (от 5 до 1440).\n\n"
                             "Например:\n"
                             "`120` для 2 часов\n"
                             "`180` для 3 часов\n"
                             "`300` для 5 часов\n"
                             "`720` для 12 часов\n"
                             "`1440` для 24 часов\n\n"
                             "Для отмены нажмите /cancel",
                             parse_mode="Markdown")
        await state.set_state(UserStates.waiting_for_interval)
        return

    try:
        interval_min = int(args.strip())
        interval_sec = interval_min * 60

        if interval_min < 5 or interval_min > 1440:
            raise ValueError("Недопустимый интервал")

        user_id = message.from_user.id
        # Сохраняем интервал и перезапускаем задачу
        await db.set_user_interval(user_id, interval_sec)
        await _restart_news_check(user_id, interval_sec, message)
        await state.clear()

    except ValueError:
        await message.answer("❌ Некорректное значение. Введите число от 5 до 1440.")
    except Exception as e:
        await message.answer("⚠️ Произошла внутренняя ошибка. Мы уже работаем над этим!")
        logging.error("Ошибка в set_interval_handler: %s", e)

@router.message(UserStates.waiting_for_interval)
async def process_interval_input(message: Message, state: FSMContext):

    # Сбрасываем состояние если сообщение - команда
    if message.text and message.text.startswith('/'):
        await message.answer("Вы отменили установку интервала 👌")
        await state.clear()
        return

    try:
        interval_min = int(message.text.strip())
        interval_sec = interval_min * 60

        if interval_min < 5 or interval_min > 1440:
            raise ValueError("Недопустимый интервал")
        
        user_id = message.from_user.id

        # Записываем интервал в БД
        await db.set_user_interval(user_id, interval_sec)
        # Обновляем статус юзера на аквтиного в is_receiving_news
        await db.set_user_receiving_news(user_id, True)
        # Перезапускаем задачу
        await _restart_news_check(user_id, interval_sec, message)
        await state.clear()

    except ValueError:
        await message.answer("🔢 Введите любое целое число от 5 до 1440.\n\n"
                             "Например:\n"
                             "`120` для 2 часов\n"
                             "`180` для 3 часов\n"
                             "`300` для 5 часов\n"
                             "`720` для 12 часов\n"
                             "`1440` для 24 часов\n\n"
                             "Для отмены нажмите /cancel",
                             parse_mode="Markdown")
    except Exception as e:
        await message.answer("⚠️ Что-то пошло не так. Попробуйте позже.")
        logging.error("Ошибка в process_interval_input: %s", e)

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
## Реагируем на кнопку "Удалить каналы" из всплывающего меню
@router.message(F.text == "Удалить каналы")
async def handle_delete_channels_button(message: Message, state: FSMContext):
    await process_delete_command(message, state)

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


############################## receive_news - Получить сводки новостей ############
## Реагиуем на кнопку "Получить новости" в inline-клавиатуре
@router.message(F.text == "Получать новости")
async def handle_receive_news_btn(message: Message, state: FSMContext):
    # Reuse /receive_news logic:
    await receive_news_handler(message, state)

@router.message(Command("receive_news"))
async def receive_news_handler(message: Message, state: FSMContext):
    # Сбрасываем состояние
    await state.clear()
    
    user_id = message.from_user.id
    
    try:
        # 1. Получаем интервал из БД
        interval_sec = await db.get_user_interval(user_id)
        
        # 2. Помечаем пользователя как активного
        await db.set_user_receiving_news(user_id, True)
        
        # 3. Инициализируем клиент Telethon
        await init_telethon_client()
        
        # 4. Перезапускаем задачу с текущим интервалом
        await _restart_news_check(user_id, interval_sec, message)
        
    except Exception as e:
        await message.answer("❌ Не удалось запустить проверку новостей.")
        logging.error("Ошибка в receive_news_handler: %s", e)


############################## stop_news Остановить получение сводки новостей #################

@router.message(F.text == "Остановить новости")
async def handle_stop_news_btn(message: Message, state: FSMContext):
    # Reuse /stop_news logic:
    await stop_news_handler(message, state)

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


##############################  FORWARD: Добавить канал через пересылку #################

@router.message(F.forward_from_chat.func(lambda chat: chat and chat.type == 'channel'))
async def handle_forwarded_message(message: Message, state: FSMContext):
    # Сбрасываем состояние, если есть активное
    # await state.clear()

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
    # scraper = TelegramScraper(user_id)

    if not channel:
        await message.answer("❌ Канал не определен. Пожалуйста, убедитесь, что вы пересылаете сообщение из публичного канала.")
        await message.delete()
        return

    if not channel.startswith("@"):
        channel = f"@{channel}"

    # try:
    #     tasks = [
    #         asyncio.create_task(
    #             summarizer.determine_channel_topic(
    #                 await scraper.scrape_messages_long_term(channel, days=DAY_RANGE_INTERVAL, limit=10)
    #             )
    #         )
    #     ]

    #     # Ожидаем завершения всех задач
    #     channel_topics = await asyncio.gather(*tasks)
    # except Exception as e:
    #     # Присуждаем пустоту если выдает ошибку
    #     channel_topics = []
    #     logging.error("\nError determine_channel_topic for user %s: %s\n", user_id, e)

    channel_topics = None
    try:
        success = await db.add_user_channels(user_id, [channel], addition_timestamp, channel_topics)
        channels = await db.fetch_user_channels(user_id)
        channels_names = ', '.join([channel["channel_name"] for channel in channels])

        if success:
            await message.answer(f"Канал {channel} успешно добавлен! ✔️ \nОбновленный список каналов: {channels_names}")
            await message.delete()
        else:
            await message.answer("Произошла ошибка при добавлении канала. Пожалуйста, попробуйте позже.")
            await message.delete()
            return
    
    except Exception as e:
        logging.error("\nError adding channels for user %s: %s\n", user_id, e)
        await message.answer("Произошла ошибка при добавлении каналов. Попробуйте позже.")

##################################### Обработка текста от юзера ####################################

#################### Обработчик для получения списка каналов
@router.message(lambda message: message.text and not message.text.startswith('/'))
async def async_process_channels_input(message: Message):

    # Если это пересылка поста из группы, то добавляем как forwarded сообщение
    if message.forward_from_chat and message.forward_from_chat.type == 'channel':
        await forwarded_message(message)
        return

    # Если это пересылка от юзера в чате, то пишем что это человек
    if message.forward_from and message.from_user:
        await message.answer("❌Кажется, вы переслали сообщение от человека 🧍, а не пост из группы.\n\n"
                             "Перешлите пост из канала)\n\n"
                             "А если вы хотите добавить чат канала, то пришлите ссылку чата или ссылку любого сообщения из чата")
        return

    user_id = message.from_user.id
    channels_text = message.text.strip()
    addition_timestamp = datetime.now().isoformat()
    # scraper = TelegramScraper(user_id)

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
    
    # Пробуем определить темы каналов
    # try:
    #     tasks = [
    #         asyncio.create_task(
    #             summarizer.determine_channel_topic(
    #                 await scraper.scrape_messages_long_term(channel, days=DAY_RANGE_INTERVAL, limit=10)
    #             )
    #         )
    #         for channel in new_channels
    #     ]

    #     # Ожидаем завершения всех задач
    #     channel_topics = await asyncio.gather(*tasks)
    # except Exception as e:
    #     # Присуждаем пустоту если выдает ошибку
    #     channel_topics = []
        # logging.error("\nError determine_channel_topic for user %s: %s\n", user_id, e)
    channel_topics = None
    try:
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


############################## Перехват обычного текста #############################

# ⚠️⚠️⚠️ этот Хэндлер Должен быть всегда в конце файла, чтобы обрабатывать остальные необработанные сообщения
# Для всех остальных сообщений
@router.message()
async def process_other_messages(message: Message, state: FSMContext):
    # Проверка на команду /cancel
    if message.text == "/cancel":
        current_state = await state.get_state()
        if current_state:
            await state.set_state(None)
            await message.answer("❌ Текущее действие отменено.")
        else:
            await message.answer("Нет активных действий для отмены 🤷")
        return

    if message.forward_from:
        await message.answer("❌Кажется, вы переслали сообщение от человека 🧍, а не пост из группы.\n\n"
                             "Перешлите пост из канала)\n\n"
                             "А если вы хотите добавить чат канала, то пришлите ссылку чата или ссылку любого сообщения из чата")
        return
    
        # Если юзер сел попой на телефон
    if  message.text and not message.text.startswith('/'):
        # Если неизвестная команды или текст или пересылка из лички
        await message.answer(
            "⚠️ Я понимаю только команды.\n\n"
            "Доступные команды:\n"
            "/set_interval    - ⏲️ установить интервал\n"
            "/delete_channels - 🗑️ удалить каналы\n"
            "/receive_news    - 📰 показывать сводки новостей\n"
            "/stop_news       - ⛔️ остановить сводку новостей\n"
            "/show_channels   - 📋 показать список ваших каналов\n"
        )
        return
    
    # Резервная обработка для всех остальных случаев
    await message.answer("Неизвестная команда. Используйте меню.")


############################## Функция обработки списка каналов #############################
def process_channel_list(channels_text: str) -> set[str]:
    """
    Обрабатывает список каналов из текста и возвращает множество корректных имен каналов.
    """
    url_pattern = re.compile(r'(?:https?://)?t\.me/([^/?]+)')
    processed_channels = set()

    for raw_channel in re.split(r'[,\s]+', channels_text.strip()):
        channel = raw_channel.strip()
        if not channel:
            continue

        # Обработка URL
        if url_match := url_pattern.search(channel):
            channel_part = url_match.group(1).split('/')[0]
            if channel_part.startswith('@'):
                channel_name = channel_part
            else:
                channel_name = f"@{channel_part}"
        # Обработка обычных упоминаний и "голых" имен
        elif re.match(r'^@?[A-Za-z0-9_]{5,}$', channel):
            channel_name = f"@{channel.lstrip('@')}"
        else:
            continue

        # Фильтрация по длине и символам
        if re.fullmatch(r'@[A-Za-z0-9_]{5,32}', channel_name):
            processed_channels.add(channel_name)

    return processed_channels

 
