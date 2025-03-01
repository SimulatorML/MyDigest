from mistralai import Mistral
from typing import List, Dict, Union

class Summarization:
    def __init__(self, api_key: str, model: str = "mistral-large-latest") -> None:
        self.client = Mistral(api_key=api_key)
        self.model = model

    def summarize_news_items(self, news: List[Dict[str, Union[str, int]]]) -> str:
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
            Each news item is represented as a dictionary with keys 'channel', 'message', and 'message_id'. 
            Here is the list: {news}. 
            If some news items are similar in context, cluster them together and produce one summary for the cluster. 
            Create a list where each line contains a summary in Russian (no longer than 150 characters) and, on the next line, 
            attach the relevant link(s) to the original news item(s). No need to add any bullet numbers, bullets etc. 
            Make sure that line with links is preceded with '📌Подробнее: ' 
            The link for each news item should be in the format:<a href="https://t.me/{{channel}}/{{message_id}}">{{channel}}</a>
            If clustered, include all relevant links separated by commas. 
            Make sure to use the exact channel name provided (without a leading '@'). 
            Structure the output so that each summary is followed on a new line by its corresponding link(s) and separated with \n'''
        )

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка генерации дайджеста: {e}")
            return "Failed to generate the summary."

    def cluster_summaries(self, summaries_text: str) -> str:
        """
        Clusters summarized news items based on similar topics.

        :param summaries_text: A string containing summaries and their respective links.
        :returns: A formatted string where similar topics are grouped together.
        """
        if not summaries_text or not summaries_text.strip():
            return "No items available for clustering."

        prompt = (
            f'''Please gather the following news summaries into topic-based clusters: \n{summaries_text}. 
            Group similar topics together and structure the output in the same format as the original summary,  
            with each summary followed by its relevant link(s).  
            Topics should be written in bold. Use HTML tags (<b> and </b>). Add additional \n after the topic. Use this format: <b> Topic </b> \n"
            No need to add any bullet numbers, bullets etc. 
            Topics must not be preceded by any symbols. 
            Topics must be in Russian language.
            Make very broad topics, try to limit number of topics to max of 5-6'''
        )

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error during clustering: {e}")
            return "Failed to produce the final digest."