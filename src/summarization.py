import logging
import asyncio
from mistralai import Mistral
from typing import List, Dict, Union
from src.utils.telegram_logger import TelegramSender

telegram_sender = TelegramSender()

class Summarization:
    def __init__(self, api_key: str, model: str = "mistral-large-latest") -> None:
        self.client = Mistral(api_key=api_key)
        self.model = model

    async def summarize_news_items(self, news: List[Dict[str, Union[str, int]]]) -> str:
        """
        Generates a summarized version of provided news items, clustering similar ones together.

        :param news: A list of dictionaries with keys:
            {
              'channel': channel name (without the '@')
              'message': text of the news
              'message_id': unique id of the message
            }
        :returns: A formatted summary string with links to the original news items.
        """
        if not news:
            return "No news items provided."

        prompt = (
            f'''You are provided with a list of news items.
            Each news item is represented as a dictionary with keys 'channel', 'message', 'message_id' and 'channel_title' 
            Here is the list: {news}. 
            If some news items are similar in context, cluster them together and produce one summary for the cluster. 
            Create a list where each line contains a summary in Russian (no longer than 150 characters) and, on the next line, 
            attach the relevant link(s) to the original news item(s). No need to add any bullet numbers, bullets etc. 
            Make sure that line with links is preceded with '<i>Источник: </i>' 
            The link for each news item should be in the format:<a href="https://t.me/{{channel}}/{{message_id}}">{{channel_title}}</a>
            If clustered, include all relevant links separated by spaces following this symbol | and space again. So this structure: link | link | link. 
            Make sure to use the exact channel name provided (without a leading '@'). 
            Structure the output so that each summary is followed on a new line by its corresponding link(s) and separated with \n'''
        )

        try:
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error("Ошибка генерации дайджеста: %s", e)
            await telegram_sender.send_text(f"⚠️ Ошибка генерации дайджеста summarize_news_items:\n\n{str(e)}")
            return "Failed to generate the summary."

    async def cluster_summaries(self, summaries_text: str) -> str:
        """
        Clusters summarized news items based on similar topics.

        :param summaries_text: A string containing summaries and their respective links.
        :returns: A formatted string where similar topics are grouped together.
        """
        if not summaries_text or not summaries_text.strip():
            return "No items available for clustering."

        prompt = (
            f''' Please categorize the following news summaries into a maximum of 5 broad, topic-based clusters.
                Each cluster should be grouped by similar topics, and the summaries should remain in their original format with each followed by its relevant link(s). 
                Each topics must be closed into HTML tags highlighting them bold: <b>Topic</b>. Don't use ** to highlight topics with bold! Never add ```html ```!
                The topic labels must be written in Russian, and each topic must be followed by a new line.
                Each topic should be introduced with a one relevant emoji. Emoji should only be placed in front of topic.
                Ensure the topics are broad and general; limit the number of topics to 5.
                Do not include bullet points, numbering, or other list formats. Keep it clean and structured as requested.
                Summaries text: \n{summaries_text}. '''
        )

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error("Error during clustering: %s", e)
            await telegram_sender.send_text(f"⚠️ Ошибка cluster_summaries:\n\n{str(e)}")
            return "Failed to produce the final digest."
