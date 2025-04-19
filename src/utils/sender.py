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
        """Отправка сообщения пользователям"""
        # Определяем список получателей
        if for_users is None:
            user_ids = self.retrieve_current_users()
        elif callable(for_users):
            user_ids = for_users()
        else:
            user_ids = for_users

        success = 0
        for user_id in user_ids:
            try:
                # Проверяем доступность чата
                chat = await self.bot.get_chat(user_id)
                if chat:
                    sent_message = await self.bot.send_message(user_id, message)

                # Пытаемся закрепить сообщение
                try:
                    await self.bot.pin_chat_message(
                        chat_id=user_id,
                        message_id=sent_message.message_id
                    )
                except Exception as pin_error:
                    logging.error(f"Ошибка закрепления для {user_id}: {pin_error}")

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
        
        message = (
            "Привет!🎉☺️\n\n"
            "Спасибо, что ты с нами❤️\n"
            "Теперь тут можно оставлять комментарии, нажми на 👉💬 /comment и поделись своим опытом:\n\n"
            "• поделись впечатлениями\n"
            "• сообщи об ошибке\n"
            "• предложи новую функцию\n"
            "📎можно прикреплять скрины и запись экрана\n\n"
            "Твой фидбек поможет сделать бота лучше 😇🙏"
            )
        # -------------------------------------------------------

        try:
            await sender.send(message, for_users)
        finally:
            await bot.session.close()  # Явное закрытие сессии

    asyncio.run(main())