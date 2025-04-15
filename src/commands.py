from aiogram.types import BotCommand
from aiogram import Bot

# Все Команды бота
ALL_COMMANDS = [

    BotCommand(command="receive_news", description="⭐️Получить новые сообщения"),
    BotCommand(command="set_interval", description="⏲️Установить интервал отправки дайджестов"),
    BotCommand(command="delete_channels", description="🗑️Удалить каналы"),
    BotCommand(command="comment", description="💬Оставить комментарий"),
    BotCommand(command="show_channels", description="📋Показать список каналов"),
    BotCommand(command="stop_news", description="⛔️Остановить сообщения"),

]

async def setup_commands(bot: Bot):
    """Установка всех команд бота"""
    await bot.set_my_commands(ALL_COMMANDS)


async def remove_commands(bot: Bot):
    """Удаление всех команд бота"""
    await bot.delete_my_commands()