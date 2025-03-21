from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

#keyboard for bot's menu
menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Получать новости'), KeyboardButton(text='Остановить новости')],
    [KeyboardButton(text='Удалить каналы'), KeyboardButton(text='Помощь')]
],
                    resize_keyboard=True,
                    input_field_placeholder="Выберете пункт меню или вызовите команду")

#keyboard for clear channels handler
clear_channels = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Да, очистить', callback_data='confirm_clear')],
    [InlineKeyboardButton(text='❌ Отмена', callback_data='cancel_clear')]
])
