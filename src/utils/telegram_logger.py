import datetime
from aiogram import Bot
import asyncio
import logging

class TelegramLogHandler:
    """
    Класс для логирования сообщений в Telegram группу
    """
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=token)
        
    async def send_log_async(self, message):
        """Асинхронная отправка сообщения в Telegram группу"""
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='HTML')
            return True
        except Exception as e:
            logging.error(f"Failed to send log to Telegram: {e}")
            return False
    
    def send_log(self, message):
        """Синхронная обертка для отправки сообщения"""
        # Создаем задачу на отправку сообщения вместо запуска нового цикла
        try:
            # Проверяем, работает ли цикл событий
            if asyncio.get_event_loop().is_running():
                # Создаем задачу в текущем цикле
                asyncio.create_task(self.send_log_async(message))
            else:
                # Если цикл событий не запущен, создаем новый для отправки сообщения
                asyncio.run(self.send_log_async(message))
        except Exception as e:
            logging.error(f"Error in sending log: {e}")
            return False
        return True

    def _format_message(self, level_emoji, level_name, message, user_id=None, extra_info=None):
        """Форматирует сообщение лога с добавлением времени, user_id и дополнительной информации"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Базовое форматирование
        log_message = f"{level_emoji} <b>{level_name}</b> [{now}]"
        
        # Добавляем user_id если он предоставлен
        if user_id:
            log_message += f" | <b>User ID:</b> {user_id}"
            
        # Добавляем основное сообщение
        log_message += f"\n{message}"
        
        # Добавляем дополнительную информацию, если она есть
        if extra_info:
            log_message += f"\n<pre>{extra_info}</pre>"
            
        return log_message

    def info(self, message, user_id=None, extra_info=None):
        """Отправка информационного сообщения"""
        log_message = self._format_message("ℹ️", "INFO", message, user_id, extra_info)
        self.send_log(log_message)
    
    def error(self, message, user_id=None, extra_info=None):
        """Отправка сообщения об ошибке"""
        log_message = self._format_message("❌", "ERROR", message, user_id, extra_info)
        self.send_log(log_message)
    
    def success(self, message, user_id=None, extra_info=None):
        """Отправка сообщения об успешной операции"""
        log_message = self._format_message("✅", "SUCCESS", message, user_id, extra_info)
        self.send_log(log_message)
    
    def warning(self, message, user_id=None, extra_info=None):
        """Отправка предупреждения"""
        log_message = self._format_message("⚠️", "WARNING", message, user_id, extra_info)
        self.send_log(log_message)