from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

#keyboard for bot's menu
menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='⭐️ Получать дайджесты'), KeyboardButton(text='⏲️ Установить интервал')],
    [KeyboardButton(text='🛑 Остановить дайджесты'), KeyboardButton(text='🗑 Удалить каналы')]
],
                    resize_keyboard=True,
                    input_field_placeholder="Выберете пункт меню или вызовите команду")

greeting_keyboard_inline = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Начать ❤️', callback_data='greeting')]
])
