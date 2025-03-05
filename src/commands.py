from aiogram.types import BotCommand
from aiogram import Bot


# Команды для работы с каналами
CHANNEL_COMMANDS = [
    BotCommand(command="add_channels", description="Добавить каналы"),
    BotCommand(command="show_channels", description="Показать список каналов"),
    BotCommand(command="delete_channels", description="Удалить каналы"),
    BotCommand(command="clear_channels", description="Очистить список каналов"),
]

# Команды для работы с дайджестами
DIGEST_COMMANDS = [

    BotCommand(command="receive_news", description="Получить новые сообщения")
]

# Общие команды
COMMON_COMMANDS = [
    BotCommand(command="help", description="Показать справку"),
]

# Все команды бота
ALL_COMMANDS = COMMON_COMMANDS + CHANNEL_COMMANDS + DIGEST_COMMANDS


async def setup_commands(bot: Bot):
    """Установка всех команд бота"""
    await bot.set_my_commands(ALL_COMMANDS)


async def remove_commands(bot: Bot):
    """Удаление всех команд бота"""
    await bot.delete_my_commands()
