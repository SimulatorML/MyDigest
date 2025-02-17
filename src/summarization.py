from mistralai import Mistral

class Summarization:
    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        self.client = Mistral(api_key=api_key)
        self.model = model

    def summarize(self, news: list, channel: str) -> str:
        # Убираем @ из начала имени канала, если он есть
        channel = channel.lstrip("@")

        prompt = (
            f"Please create a summary of each piece of news provided. Here's the list: {news}. "
            f"Create a list with the same size as the number of news pieces provided. Use bullet points. "
            f"Each summary should be in Russian and no longer than 150 characters. "
            f"Please also add link to the end of each summary. The format of the link is https://t.me/{channel}/message_id provided. Ensure that channel name must not be preceded by @. "
            f"Add the link after each of the summary pieces in following format: 📌Подробнее: https://t.me/{channel}/message_id provided. "
            f"Structure the output as follows:\nLinks must be on the next line after the summary."
        )

    client = Client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": PROMPT}],
            web_search=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Ошибка генерации дайджеста: {e}")
        return None
