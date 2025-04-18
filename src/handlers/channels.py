import asyncio
import re
import logging
import src.handlers.keyboards as kb
from datetime import datetime
from aiogram.enums import ContentType
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
from src.config import MISTRAL_KEY, DAY_RANGE_INTERVAL, GROUP_LOGS_ID
from src.summarization import Summarization
from src.handlers.messages import BOT_DESCRIPTION, TUTORIAL_STEPS

router = Router()
db = SupabaseDB(supabase)
summarizer = Summarization(api_key=MISTRAL_KEY)


class UserStates(StatesGroup):
    waiting_for_channels = State()
    waiting_for_delete = State()
    selecting_channels = State()
    try_selecting_channels = State()
    waiting_for_interval = State()
    waiting_for_comment = State()


############################## Приветствие и тъюториал ###############################

@router.message(CommandStart())
async def process_start_command(message: Message):
    """
       Processes the /start command by registering the user (if not exists) and sending a greeting message.

       :param message: Incoming message object that triggered the /start command.
       :returns: None. Sends a message with BOT_DESCRIPTION and greeting_keyboard_inline.
    """

    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "unknown"
    login_timestamp = datetime.now().isoformat()

    user_exists = await db.fetch_user(user_id)
    if not user_exists:
        await db.add_user(user_id, username, login_timestamp)  # check_interval=3600 - по умолчанию

    await message.answer(text=BOT_DESCRIPTION, reply_markup=kb.greeting_keyboard_inline)


@router.callback_query(lambda c: c.data and c.data == "greeting")
async def greeting_callback_handler(callback: CallbackQuery):
    """
       Handles the callback query when the "greeting" button is pressed and sends the first tutorial step.

       :param callback: CallbackQuery object from the pressed inline button.
       :returns: None. Sends a new message with the first tutorial step and corresponding keyboard.
    """

    await callback.answer()

    # Запускаем обучение: отправляем первый шаг туториала.
    step_index = 0
    total_steps = len(TUTORIAL_STEPS)
    text = TUTORIAL_STEPS[step_index]
    keyboard = get_tutorial_keyboard(step_index, total_steps)

    await callback.message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


def get_tutorial_keyboard(step_index: int, total_steps: int) -> InlineKeyboardMarkup:
    """
    Generates an inline keyboard for the tutorial navigation with "Back", "Next", and "Try" buttons.

    :param step_index: Current step index of the tutorial.
    :param total_steps: Total number of tutorial steps.
    :returns: InlineKeyboardMarkup object with navigation buttons.
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
    # Adding "Try" button
    try_button = [InlineKeyboardButton(
        text="Попробовать",
        callback_data="try"
    )]

    return InlineKeyboardMarkup(inline_keyboard=[buttons, try_button])


@router.callback_query(lambda c: c.data and c.data.startswith("tutorial_next_"))
async def tutorial_next_handler(callback: CallbackQuery):
    """
        Handles the callback query for moving to the next tutorial step.

        :param callback: CallbackQuery object containing data with the current step index.
        :returns: None. Edits the current message with the next tutorial step text and updated keyboard.
    """

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
    """
        Handles the callback query for moving back to the previous tutorial step.

        :param callback: CallbackQuery object containing data with the current step index.
        :returns: None. Edits the current message with the previous tutorial step text and updated keyboard.
    """

    await callback.answer()

    data = callback.data  # e.g. "tutorial_back_2"
    current_step = int(data.split("_")[-1])
    prev_step = current_step - 1

    if prev_step >= 0:
        new_text = TUTORIAL_STEPS[prev_step]
        new_kb = get_tutorial_keyboard(prev_step, len(TUTORIAL_STEPS))
        await callback.message.edit_text(new_text, reply_markup=new_kb, parse_mode="HTML")


########################### Добавленная логика "Попробовать" ###########################

@router.callback_query(lambda c: c.data == "try")
async def try_handler(callback: CallbackQuery, state: FSMContext):
    """
    Handles the "Try" callback by sending a message with a list of example channels for selection.

    :param callback: CallbackQuery object triggered by the "Try" button.
    :param state: FSMContext for storing selected channels.
    :returns: None. Sends a message with an inline keyboard of example channels.
    """

    await callback.answer()

    # Список каналов. Ключ display_name - то, что увидит пользователь на кнопке, link - реальное канал в Telegram
    example_channels = [
        {"display_name": "РИА", "link": "@rian_ru"},
        {"display_name": "Ридовка", "link": "@readovkanews"},
        {"display_name": "KarpovCourses",  "link": "@KarpovCourses"},
        {"display_name": "Спортс", "link": "@sportsru"},
        {"display_name": "Москвач", "link": "@moscowach"},
        {"display_name": "GPTMainNews", "link": "@GPTMainNews"},
        {"display_name": "Кинопоиск",  "link": "@kinopoisk"},
        {"display_name": "BOGDANISSIMO", "link": "@bogdanisssimo"},
    ]

    # Сохраняем их в state
    await state.update_data(try_channels=example_channels, try_selected=[])

    # Устанавливаем состояние для выбора каналов
    await state.set_state(UserStates.try_selecting_channels)

    builder = InlineKeyboardBuilder()

    for i, ch in enumerate(example_channels):
        builder.button(
            text=ch["display_name"],
            callback_data=f"try_select_{i}"
        )

    builder.adjust(2)  # Две кнопки в одной строке

    # Добавим кнопку подтверждения и кнопку "Добавить свой канал"
    builder.row(
        InlineKeyboardButton(
            text="Подтвердить и выслать дайджест",
            callback_data="try_confirm"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Добавить свой канал",
            callback_data="try_add_channel"
        )
    )

    # Отправляем сообщение с клавиатурой
    await callback.message.answer(
        "Выберите интересующие каналы или добавьте свои:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(lambda c: c.data.startswith("try_select_"), UserStates.try_selecting_channels)
async def try_select_channel_callback(callback: CallbackQuery, state: FSMContext):
    """
    Handles channel selection toggling. Updates the list of selected channels and refreshes the inline keyboard.

    :param callback: CallbackQuery object with data indicating the index of the selected channel.
    :param state: FSMContext for storing and updating selected channels.
    :returns: None. Edits the current message to update the selection status.
    """
    await callback.answer()

    # Извлекаем индекс канала:
    index_str = callback.data[len("try_select_"):]
    index = int(index_str)

    data = await state.get_data()

    example_channels = data.get("try_channels", [])
    selected_indices = data.get("try_selected", [])

    # если этот индекс уже есть в selected_indices - убираем его, иначе добавляем
    if index in selected_indices:
        selected_indices.remove(index)
    else:
        selected_indices.append(index)

    # Обновляем в state
    await state.update_data(try_selected=selected_indices)

    # Теперь заново строим клавиатуру, помечая выбранные каналы "📌"
    builder = InlineKeyboardBuilder()

    for i, ch in enumerate(example_channels):
        if i in selected_indices:
            # Добавляем "📌" к названию
            builder.button(
                text=f"📌 {ch['display_name']}",
                callback_data=f"try_select_{i}"
            )
        else:
            builder.button(
                text=ch['display_name'],
                callback_data=f"try_select_{i}"
            )

    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(
            text="Подтвердить и выслать дайджест",
            callback_data="try_confirm"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Добавить свой канал",
            callback_data="try_add_channel"
        )
    )

    # Обновляем предыдущее сообщение
    await callback.message.edit_text(
        "Выберите интересующие каналы или добавьте свои:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(lambda c: c.data == "try_confirm", UserStates.try_selecting_channels)
async def try_confirm_callback(callback: CallbackQuery, state: FSMContext):
    """
    Processes the confirmation of selected channels:
      1. Retrieves selected channel indices from the state.
      2. Converts them into real channel links.
      3. Links channels to the user.
      4. Starts automatic news fetching.
      5. Sends a success message.

    :param callback: CallbackQuery object triggered by pressing the confirmation button.
    :param state: FSMContext containing the current selection and channel data.
    :returns: None. Performs database operations and starts background news retrieval.
    """
    data = await state.get_data()
    example_channels = data.get("try_channels", [])
    selected_indices = data.get("try_selected", [])

    if not selected_indices:
        await callback.answer("Вы не выбрали ни одного канала!", show_alert=True)
        return

    # Собираем реальные ссылки
    links = [example_channels[i]["link"] for i in selected_indices]

    # Связываем эти каналы с текущим пользователем
    user_id = callback.from_user.id
    addition_timestamp = datetime.now().isoformat()

    try:
        channel_ids = await db.fetch_channel_ids(links)
        if channel_ids:
            await db.link_user_channels(user_id, channel_ids, addition_timestamp)
    except Exception as e:
        logging.error("Ошибка при добавлении каналов из 'Попробовать': %s", e)
        await callback.message.answer("Произошла ошибка при добавлении каналов. Попробуйте позже.")
        return

    # запускаем получение новостей,

    try:
        await db.set_user_receiving_news(user_id, True)
        scraper = TelegramScraper(user_id)

        # Инициализируем клиент Telethon (если не инициализирован)
        await init_telethon_client()

        if scraper.stop_auto_news_check(user_id):
            await callback.message.answer("🔄 Перезапускаю фоновую проверку новостей...")

        # по умолчанию interval = 3600, когда новый юзер приходит
        task = asyncio.create_task(
            scraper.start_auto_news_check(
                user_id
            )
        )
        TelegramScraper.running_tasks[user_id] = task

        # Сообщим, что фоновые дайджесты запущены
        await callback.message.answer(
            "✅ Каналы добавлены и запущена фоновая проверка новостей. "
            f"Вы будете получать обновления каждые {3600 // 60} минут.",
            reply_markup=kb.menu
        )
    except Exception as e:
        logging.error("Ошибка при запуске фоновой проверки после try_confirm: %s", e)
        await callback.message.answer("❌ Произошла ошибка при запуске проверки новостей. Попробуйте позже.")
        return

    # Сбрасываем состояние FSM
    await state.clear()

@router.callback_query(lambda c: c.data == "try_add_channel")
async def try_add_channel_callback(callback: CallbackQuery, state: FSMContext):
    """
    Handles the callback when the user chooses to add a custom channel.
    Prompts the user to send a channel link or forward a message from a public channel.

    :param callback: CallbackQuery object triggered by the "Добавить свой канал" button.
    :param state: FSMContext (unused in this function, but provided for consistency).
    :returns: None. Sends a message instructing the user on how to add a channel.
    """
    await callback.answer()
    await callback.message.answer("Хорошо, пришлите ссылку на канал или перешлите пост из открытого канала. \n\n"
                                  "Для быстрой ориентации пользуйтесь кнопками меню снизу. 👇",
                                  reply_markup=kb.menu)


############################## set_interval - интервал для получения дайджестов  #####################

### Устанавливаем интервал
@router.message(Command("set_interval"))
async def set_interval_handler(message: Message, command: CommandObject, state: FSMContext):
    """
    Handles the /set_interval command to set the interval for receiving digests.

    This function prompts the user to input an interval in minutes if not provided
    as arguments. It then processes the arguments to validate and set the interval.
    If the interval is valid, it updates the user's interval setting and restarts the
    news checking task with the new interval.

    :param message: The incoming message object containing the command.
    :param command: The CommandObject containing parsed command arguments.
    :param state: The FSMContext for managing the state of the conversation.
    :returns: None. Sends messages to the user and updates their interval settings.
    """

    args = command.args if command else None
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
    await process_interval_args(message, args, state)


# Отдельная функция для обработки аргументов
async def process_interval_args(message: Message, args: str, state: FSMContext):
    """
    Process and validate interval arguments for setting the user's news digest interval.

    This function parses the provided interval argument, converts it to seconds, and
    validates that it falls within the acceptable range. If valid, it updates the user's
    interval settings in the database and restarts the news checking task. If invalid,
    it prompts the user for a correct value.

    :param message: The incoming message object containing the command.
    :param args: The string arguments from the command representing the interval in minutes.
    :param state: The FSMContext for managing the state of the conversation.
    :returns: None. Sends messages to the user and updates their interval settings.
    :raises: ValueError if the interval is out of the allowed range.
    :raises: General exceptions are logged and a user-friendly error message is sent.
    """

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

# Кнопка в меню
@router.message(F.text == "⏲️ Установить интервал")
async def handle_interval_btn(message: Message, state: FSMContext):
    # Устанавливаем состояние ожидания интервала
    await message.answer(
        "📝 Введите интервал в минутах (от 5 до 1440).\n\n"
        "Например:\n"
        "`120` для 2 часов\n"
        "`180` для 3 часов\n"
        "`300` для 5 часов\n"
        "`720` для 12 часов\n"
        "`1440` для 24 часов\n\n"
        "Для отмены нажмите /cancel",
        parse_mode="Markdown"
    )
    await state.set_state(UserStates.waiting_for_interval)

@router.message(UserStates.waiting_for_interval)
async def process_interval_input(message: Message, state: FSMContext):
    """
    Handles the message containing the interval for setting the user's news digest interval.

    This function processes the user's input as a string, parses it into an integer, and validates
    that it falls within the acceptable range. If valid, it updates the user's interval settings in
    the database and restarts the news checking task. If invalid, it prompts the user for a correct
    value. If the message is a command, it resets the state to the default state and sends a message
    indicating that the interval setup was cancelled.
    """
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


############################## /comment - оставить комментарий ##############################

@router.message(Command("comment"))
async def start_comment(message: Message, state: FSMContext):
    """Запускает процесс сбора комментария"""
    await message.answer(
        "📝 Напишите ваш комментарий. Например:\n\n"
        "• предложите новую функцию\n"
        "• сообщите об ошибке\n"
        "• поделитесь впечатлениями\n\n"
        "Чтобы отменить, нажмите /cancel"
    )
    await state.set_state(UserStates.waiting_for_comment)

@router.message(UserStates.waiting_for_comment)
async def save_comment(message: Message, state: FSMContext):
    user_info = (
        f"👤 Пользователь: @{message.from_user.username}\n"
        f"🆔 ID: {message.from_user.id}"
    )

    try:
        # Формируем подпись с комментарием (если есть)
        caption = user_info
        if message.caption or message.text:
            caption += f"\n\n📝 Комментарий:\n{message.caption or message.text}"

        # Отправляем в группу
        if message.content_type == ContentType.TEXT:
            await message.bot.send_message(
                GROUP_LOGS_ID,
                f"{user_info}\n\n📝 Комментарий:\n{message.text}"
            )
        elif message.content_type == ContentType.PHOTO:
            await message.bot.send_photo(
                GROUP_LOGS_ID,
                message.photo[-1].file_id,
                caption=caption
            )
        elif message.content_type == ContentType.VIDEO:
            await message.bot.send_video(
                GROUP_LOGS_ID,
                message.video.file_id,
                caption=caption
            )
        elif message.content_type == ContentType.DOCUMENT:
            await message.bot.send_document(
                GROUP_LOGS_ID,
                message.document.file_id,
                caption=caption
            )

        await message.answer("✅ Ваш комментарий отправлен команде!")
        
    except Exception as e:
        logging.error(f"Ошибка пересылки: {str(e)}")
        await message.answer("❌ Не удалось отправить комментарий")
        
    await state.clear()

# @router.message(UserStates.waiting_for_comment)
# async def save_comment(message: Message, state: FSMContext):

#     # Если это не текстовое сообщение
#     if not message.text:
#         await message.answer("❌ Пока мы обрабатываем только текстовые комментарии 🥲")
#         return

#     # Сбрасываем состояние если сообщение - команда
#     if message.text and message.text.startswith('/'):
#         await message.answer("отменили 👌")
#         await state.clear()
#         return
    
#     # Сохраняет комментарий в базу
#     user_id = message.from_user.id
#     comment = message.text.strip()

#     try:
#         # Добавляем комментарий в массив
#         success = await db.add_user_comment(user_id, comment)
#         if success:
#             await message.answer("✅ Ваш комментарий принят!")
#         else:
#             await message.answer("❌ Ошибка при сохранении комментария")
            
#     except Exception as e:
#         logging.error(f"Comment error: {str(e)}")
#         await message.answer("⚠️ Произошла ошибка, попробуйте позже")
        
#     await state.clear()

############################## show_channels - Показать каналы #####################

@router.message(Command(commands="show_channels"))
async def process_show_channels_command(message: Message):
    """
    Handles the /show_channels command to display the user's subscribed channels.

    This function fetches the list of channels associated with the user from the database.
    If the user has channels, it sends a message listing their channel names. If not, it
    informs the user that they have no added channels.

    :param message: The incoming message object containing the command.
    :type message: Message
    :returns: None. Sends a message listing the user's channels or indicating none are added.
    """

    user_id = message.from_user.id
    channels = await db.fetch_user_channels(user_id)

    if channels:
        channel_names = [channel["channel_name"] for channel in channels]
        await message.answer(f"Ваши каналы:\n{', '.join(channel_names)}")
    else:
        await message.answer("У вас пока нет добавленных каналов.")



############################## delete_channels - Удалить каналы #################
## Реагируем на кнопку "Удалить каналы" из всплывающего меню
@router.message(F.text == "🗑 Удалить каналы")
async def handle_delete_channels_button(message: Message, state: FSMContext):
    await process_delete_command(message, state)

# Обработчик для удаления каналов
@router.message(Command(commands="delete_channels"))
async def process_delete_command(message: Message, state: FSMContext):
    """
    Handles the /delete_channels command and presents the user with a list of their channels to delete.

    If the user has no channels, it sends a message indicating that. Otherwise, it sets the user's state to
    `UserStates.selecting_channels` and sends a message with an inline keyboard where each channel is
    a button. The user can then select channels to delete by clicking on them. The selected channels are
    stored in the user's state. The user can confirm the deletion by clicking on the "Подтвердить" button
    or cancel by clicking on the "Отмена" button. If the user wants to delete all channels at once, they
    can click on the "Удалить все каналы" button.
    """
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
    """
    Handles the callback when the user chooses to add a custom channel.
    Prompts the user to send a channel link or forward a message from a public channel.

    :param callback: CallbackQuery object triggered by the "Добавить свой канал" button.
    :param state: FSMContext (unused in this function, but provided for consistency).
    :returns: None. Sends a message instructing the user on how to add a channel.
    """
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
@router.message(F.text == "⭐️ Получать новости")
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

@router.message(F.text == "🛑 Остановить новости")
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
        "Для повторного получения новостей нажмите на кнопку <b>Получить новости</b>", parse_mode="HTML"
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

        processed_groups.add(message.media_group_id)
        await state.update_data(processed_media_groups=processed_groups)
    await forwarded_message(message)


async def forwarded_message(message: Message):
    """
    Processes a forwarded message to add a channel for the user.

    This function handles messages forwarded from public channels. It attempts to
    link the channel to the user if it already exists in the database, or adds
    the channel if it is not present. The function provides feedback to the user
    on the success or failure of the operation.

    :param message: The message object containing the forwarded channel message.
    :type message: Message
    :returns: None. Sends messages to the user for operation status.
    :raises Exception: Logs and informs the user if there's an error during the process.
    """

    user_id = message.from_user.id
    addition_timestamp = datetime.now().isoformat()
    channel = message.forward_from_chat.username
    scraper = TelegramScraper(user_id)

    if not channel:
        await message.answer("❌ Канал не определен. Пожалуйста, убедитесь, что вы пересылаете сообщение из публичного канала.")
        return

    channel = f"@{channel}" if not channel.startswith("@") else channel

    try:
        exist_channel_id = await db.fetch_channel_id(channel)
        if exist_channel_id:
            linking_user_channel = await db.link_user_single_channel(user_id, exist_channel_id, addition_timestamp)
            if linking_user_channel:
                await message.answer(f"Канал {channel} успешно добавлен! ✔️\n\n Список ваших каналов - команда /show_channels")
                await message.delete()
            else:
                await message.answer("Ошибка при добавлении канала. Пожалуйста, попробуйте позже.")

        else:
            messages = await scraper.scrape_messages_long_term(channel, days=DAY_RANGE_INTERVAL, limit=15)
            channel_topic = await summarizer.determine_channel_topic(messages)

            adding_channel = await db.add_single_channel(channel, channel_topic, addition_timestamp)
            if adding_channel:
                channel_id = await db.fetch_channel_id(channel)
                await db.link_user_single_channel(user_id, channel_id, addition_timestamp)
                await message.answer(f"Канал {channel} успешно добавлен! ✔️\n\n Список ваших каналов - команда /show_channels")
                await message.delete()
            else:
                await message.answer("Ошибка при добавлении канала. Пожалуйста, попробуйте позже.")
    except Exception as e:
        logging.error("\nError adding channel for user %s: %s\n", user_id, e)
        await message.answer("Произошла ошибка при добавлении канала. Пожалуйста, попробуйте позже.")

##################################### Обработка текста от юзера ####################################

#################### Обработчик для получения списка каналов
@router.message(lambda message: message.text and not message.text.startswith('/'))
async def async_process_channels_input(message: Message):
    """
    Handles a message from a user and attempts to add channels from the text.
    If the message is a forwarded message from a channel, it calls the forwarded_message function.
    If the message is a forward from a user in a chat, it replies that the message is from a person, not a channel.
    Otherwise, it processes the message as a list of channels to add, scrapes the topics of the channels,
    adds the channels to the database, and links the channels to the user.

    :param message: The message object containing the text of the channels to add.
    :type message: Message
    :returns: None. Sends messages to the user for operation status.
    :raises Exception: Logs and informs the user if there's an error during the process.
    """
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
        new_channels = list(new_channels)

        channel_ids = await db.fetch_channel_ids(new_channels)
        if channel_ids:
            await db.link_user_channels(user_id, channel_ids, addition_timestamp)
            new_channels_list = ', '.join(new_channels)
            await message.answer(f"Каналы {new_channels_list} успешно добавлены! ✔️\n\n Список ваших каналов - команда /show_channels")

        else:
            topics = []
            for channel in new_channels:
                messages = await scraper.scrape_messages_long_term(channel, days=DAY_RANGE_INTERVAL, limit=15)
                channel_topic = await summarizer.determine_channel_topic(messages)
                topics.append(channel_topic)

            await db.add_channels(new_channels, topics, addition_timestamp)
            channel_ids = await db.fetch_channel_ids(new_channels)
            await db.link_user_channels(user_id, channel_ids, addition_timestamp)

            new_channels_list = ', '.join(new_channels)
            await message.answer(f"Каналы {new_channels_list} успешно добавлены! ✔️\n\n Список ваших каналов - команда /show_channels")

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

############################## Доп функции ##############################


############################## Функция для перезапуска дайджеста
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
