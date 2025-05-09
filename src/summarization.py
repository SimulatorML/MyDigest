import logging
import asyncio
from mistralai import Mistral
from typing import List, Dict, Union
import random

class Summarization:
    def __init__(self, api_key: str, model: str = "mistral-large-latest") -> None:
        self.api_key = api_key
        self.model = model

    async def _mistral_request(self, prompt: str, max_retries: int = 5) -> str:
        """Makes request to Mistral API with retry&backoff logic
        :param prompt: The prompt to be made and a number of retries"""

        retry_delay = 1
        async with Mistral(api_key=self.api_key) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.chat.complete_async(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    if "Status 429" in str(e):
                        # Проверяем наличие заголовка Retry-After
                        retry_after = getattr(e, 'headers', {}).get('Retry-After', retry_delay)
                        retry_delay = min(float(retry_after), 60)
                        logging.warning("Rate limit exceeded. Attempt %s/%s. Retrying in %s seconds...",
                                        attempt + 1, max_retries, retry_delay)
                        await asyncio.sleep(retry_delay + random.uniform(0, 1))
                        retry_delay *= 2  # Увеличиваем задержку экспоненциально
                    else:
                        raise
                raise Exception("Max retries exceeded")

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
            return await self._mistral_request(prompt)
        except Exception as e:
            logging.error("Error during summarization: %s", e)
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
                Summaries text: \n{summaries_text}. 
                Make sure that the resulting output does not exceed 4000 characters. And ensure that the output is formatted in Russian.
                The output must not have any additional symbols other than mentioned above.
         '''
        )
        try:
            return await self._mistral_request(prompt)
        except Exception as e:
            logging.error("Error during clustering: %s", e)
            return "Failed to produce the final digest."

    async def determine_channel_topic(self, messages: List[Dict[str, Union[str, int]]]) -> List[str]:
        """
        Determines channel topics based on recent posts.

        :param messages: List of dictionaries with keys:
            {
              'channel': channel name (without the '@'),
              'message': text of the news,
              'message_id': id of the message
            }
        :returns: A string with the determined channel topic.
        """
        if not messages:
            return ["Общая тематика"]

        # Если сообщения уже в нужном формате, используем их
        if all(key in messages[0] for key in ["channel", "message", "message_id"]):
            formatted_messages = messages
        else:
            formatted_messages = [
                {
                    "channel": msg.get("channel_title", "Неизвестный канал"),
                    "message": msg["message"],
                    "message_id": msg["message_id"]
                } for msg in messages
            ]

        prompt = (
            f'''Analyze the list of the channel's latest messages: {formatted_messages}.
                Determine the main topic of the channel and return it as a brief, specific, and clear formulation.
                The topic should consist of a maximum of three words (you can use commas or conjunctions if necessary).
                The topic should be in Russian.
                If the messages contain special terms like "AI", "IT", "ML" or company/brand/enterprise names in any language (Russian, Spanish, French, etc.), keep them in their original form if they are part of the final topic of the channel.
                Do not enclose the topic in quotes.
                Do not add any explanations or reasoning.
                The topic should not start with phrases like "The main topic of the channel" or "Based on the provided messages".
                Just return the topic in its pure form.'''
        )

        try:
            raw_topic = await self._mistral_request(prompt)
            list_topic = list(map(str.strip, raw_topic.split(',')))
            return list_topic
        except Exception as e:
            logging.error("\nError determining channel topic: %s\n", e)
            return "Failed to determine channel topic."
