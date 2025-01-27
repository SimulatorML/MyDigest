from multiprocessing.context import DefaultContext
from urllib.parse import uses_query

from g4f.client import Client

# first option
def summarize(news: list, channel: str) -> list:

    PROMPT = (f"Please create a summary of each piece of news provided. Here's the list: {news}. "
              f"Create a list with the same size as the number of news pieces provided. Use bullet points."
              f"Each summary should be in Russian and no longer than 150 characters. "
              f"Please also add link to the end of each summary. The format of the link is https://t.me/%{channel}%/%message_id provided%"
              f"Add the link after each of the summary pieces in following format: 📌Подробнее: https://t.me/%{channel}%/%message_id provided% "
              f"Structure the output as follows:\n Links must be on the next line after the summary.")

    client = Client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": PROMPT}],
        web_search=False
    )
    return response.choices[0].message.content