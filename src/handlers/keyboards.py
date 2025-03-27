from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

#keyboard for bot's menu
menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Получать новости'), KeyboardButton(text='Остановить новости')],
    [KeyboardButton(text='Удалить каналы'), KeyboardButton(text='Помощь')]
],
                    resize_keyboard=True,
                    input_field_placeholder="Выберете пункт меню или вызовите команду")
