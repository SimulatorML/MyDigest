from functools import wraps
import traceback
from typing import Optional, Callable, Any
from .telegram_logger import TelegramLogHandler

def log_execution(logger: TelegramLogHandler, include_user_id: bool = False):
    """
    Декоратор для логирования выполнения обычных (синхронных) функций
    
    Args:
        logger: Экземпляр логгера TelegramLogHandler
        include_user_id: Флаг для включения извлечения user_id из аргументов
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__
            
            # Извлечение user_id из аргументов, если требуется
            user_id = None
            if include_user_id:
                user_id = _extract_user_id(args, kwargs)
            
            # Логирование начала выполнения
            logger.info(f"Starting execution of {func_name}", user_id=user_id)
            
            # Выполнение функции с отловом ошибок
            try:
                result = func(*args, **kwargs)
                logger.success(f"Function {func_name} completed successfully", user_id=user_id)
                return result
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(
                    f"Function {func_name} failed with error: {str(e)}", 
                    user_id=user_id,
                    extra_info=error_traceback
                )
                raise
        return wrapper
    return decorator

def log_async_execution(logger: TelegramLogHandler, include_user_id: bool = False):
    """
    Декоратор для логирования выполнения асинхронных функций
    
    Args:
        logger: Экземпляр логгера TelegramLogHandler
        include_user_id: Флаг для включения извлечения user_id из аргументов
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__
            
            # Извлечение user_id из аргументов, если требуется
            user_id = None
            if include_user_id:
                user_id = _extract_user_id(args, kwargs)
            
            # Логирование начала выполнения
            logger.info(f"Starting execution of async {func_name}", user_id=user_id)
            
            # Выполнение функции с отловом ошибок
            try:
                result = await func(*args, **kwargs)
                logger.success(f"Async function {func_name} completed successfully", user_id=user_id)
                return result
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(
                    f"Async function {func_name} failed with error: {str(e)}", 
                    user_id=user_id,
                    extra_info=error_traceback
                )
                raise
        return wrapper
    return decorator

def log_telegram_handler(logger: TelegramLogHandler):
    """
    Декоратор для логирования обработчиков Telegram бота
    
    Args:
        logger: Экземпляр логгера TelegramLogHandler
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs) -> Any:
            # Извлечение информации о пользователе из объекта update
            user_id = update.effective_user.id if update.effective_user else "Unknown"
            username = update.effective_user.username if update.effective_user else "Unknown"
            chat_id = update.effective_chat.id if update.effective_chat else "Unknown"
            
            # Получение текста сообщения, если доступно
            command = update.message.text if update.message else "No text"
            
            # Логирование входящей команды
            logger.info(
                f"Handling command: {command}", 
                user_id=user_id, 
                extra_info=f"Username: @{username}\nChat ID: {chat_id}"
            )
            
            # Выполнение обработчика с отловом ошибок
            try:
                result = await func(update, context, *args, **kwargs)
                logger.success(f"Command processed successfully", user_id=user_id)
                return result
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(
                    f"Error processing command: {str(e)}", 
                    user_id=user_id,
                    extra_info=f"Command: {command}\n{error_traceback}"
                )
                raise
        return wrapper
    return decorator

def _extract_user_id(args, kwargs) -> Optional[str]:
    """
    Вспомогательная функция для извлечения user_id из аргументов функции
    
    Возвращает:
        user_id если найден, иначе None
    """
    # Проверка на наличие user_id в именованных аргументах
    if 'user_id' in kwargs:
        return kwargs['user_id']
    
    # Проверка для случаев, когда первый аргумент - это объект update из Telegram
    if args and hasattr(args[0], 'effective_user') and args[0].effective_user:
        return args[0].effective_user.id
    
    # Проверка для случаев с другой структурой
    for arg in args:
        # Если аргумент - словарь с user_id
        if isinstance(arg, dict) and 'user_id' in arg:
            return arg['user_id']
        
        # Если аргумент - объект с атрибутом user_id
        if hasattr(arg, 'user_id'):
            return arg.user_id
    
    return None