import httpx
import logging
import asyncio
from datetime import datetime
from src.config import GROUP_LOGS_ID, TELEGRAM_BOT_TOKEN, TURN_TG_LOGGER, TITLE_TG_LOGGER

class TelegramSender:
    def __init__(
        self,
        token: str = TELEGRAM_BOT_TOKEN,
        turn: bool = TURN_TG_LOGGER,
        title: str = TITLE_TG_LOGGER
    ):
        self.token = token
        self.url = f"https://api.telegram.org/bot{self.token}"
        self.turn = turn
        self.title = title

    async def send_text(self, text: str, channel_id: str = GROUP_LOGS_ID) -> None:
        """Асинхронная отправка сообщения в Telegram."""
        if not self.turn:
            logging.info("Телеграм-логирование отключено (TURN_TG_LOGGER=False)")
            return

        if not channel_id:
            logging.error("GROUP_LOGS_ID не задан. Сообщение не отправлено.")
            return

        full_text = (
            f"{self.title}\n"
            f"{text}\n\n"
            f"{datetime.now()}"
        )

        try:
            await asyncio.sleep(0.6) # задержка перед отправкой чтобы не спамить
            async with httpx.AsyncClient(timeout=5) as client:  # Таймаут 5 сек если долго не будет отвечать
                response = await client.post(
                    f"{self.url}/sendMessage",
                    json={
                        "chat_id": channel_id,
                        "text": full_text
                    }
                )
                response.raise_for_status()  # Проверка статуса 4xx/5xx

        except httpx.HTTPStatusError as e:
            logging.error(f"Ошибка Telegram API: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logging.error(f"Ошибка подключения: {str(e)}")
            raise

# Глобальный экземпляр
telegram_sender = TelegramSender()