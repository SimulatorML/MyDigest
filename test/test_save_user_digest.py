import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from src.data.database import SupabaseDB, supabase
from src.summarization import summarize

db = SupabaseDB(supabase)

async def test_save_user_digest():
    user_id = 1  # Замените на реальный user_id
    channel_id = 1  # Замените на реальный channel_id
    channel_name = "@channel_example"  # Замените на реальный канал
    messages = [
        {"message_id": 1, "message": "Пример сообщения 1", "message_date": datetime.now()},
        {"message_id": 2, "message": "Пример сообщения 2", "message_date": datetime.now()},
    ]

    # Создаём дайджест
    digest_content = summarize(messages, channel_name)
    creation_timestamp = datetime.now().isoformat()

    # Сохраняем дайджест в БД
    success = await db.save_user_digest(user_id, channel_id, digest_content, creation_timestamp)
    if success:
        print(f"Дайджест для канала {channel_name} успешно сохранён.")
    else:
        print(f"Ошибка при сохранении дайджеста для канала {channel_name}.")

if __name__ == "__main__":
    asyncio.run(test_save_user_digest())