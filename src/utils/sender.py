import logging
from typing import List, Union, Callable
from aiogram import Bot
from src.data.database import SupabaseDB

logger = logging.getLogger(__name__)

class AnnouncementSender:
    def __init__(self, bot: Bot, db: SupabaseDB):
        self.bot = bot
        self.db = db

    def retrieve_current_users(self) -> List[int]:
        """Получить ID всех активных пользователей из БД."""
        try:
            response = (
                self.db.client.table("users")
                .select("user_id")
                .eq("is_receiving_news", True)
                .execute()
            )
            return [user["user_id"] for user in response.data]
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return []

    async def send(
        self,
        message: str,
        for_users: Union[List[int], Callable[[], List[int]]] = None
    ):
        """Отправка сообщения пользователям."""
        # Определяем список получателей
        if for_users is None:
            user_ids = self.retrieve_current_users()
        elif callable(for_users):
            user_ids = for_users()
        else:
            user_ids = for_users

        # Отправка
        success = 0
        for user_id in user_ids:
            try:
                await self.bot.send_message(user_id, message)
                success += 1
            except Exception as e:
                logger.error(f"Ошибка отправки {user_id}: {e}")

        logger.info(f"Успешно отправлено: {success}/{len(user_ids)}")

if __name__ == "__main__":
    import asyncio
    from src.config import TELEGRAM_BOT_TOKEN
    from src.data.database import supabase

    async def main():
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        db = SupabaseDB(supabase)
        sender = AnnouncementSender(bot, db)

        # Конфигурация ------------------------------------------
        # Вариант 1: Отправить всем активным пользователям
        for_users = sender.retrieve_current_users
        
        # # Вариант 2: Отправить конкретным юзерам
        # for_users = [1006278099]  # Список ID
        
        message = "🎉 Появилась возможность отправки комментариев!"
        # -------------------------------------------------------

        try:
            await sender.send(message, for_users)
        finally:
            await bot.session.close()  # Явное закрытие сессии

    asyncio.run(main())