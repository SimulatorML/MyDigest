from aiogram.types import BotCommand

# Все Команды бота
ALL_COMMANDS = [

    BotCommand(command="receive_news", description="Получить новые сообщения"),
    BotCommand(command="delete_channels", description="Удалить каналы"),
    BotCommand(command="show_channels", description="Показать список каналов"),
    BotCommand(command="stop_news", description="Остановить сообщения"),

]
