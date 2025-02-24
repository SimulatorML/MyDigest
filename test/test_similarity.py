import nltk
import string
from nltk import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
nltk.download('punkt_tab')
nltk.download('stopwords')
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np

import numpy as np
from simple_elmo import ElmoModel
from numpy.linalg import norm


string1 = "Криптобиржу Bybit хакнули на $1,4 млрд"\
          "С холодного кошелька биржи был зафиксирован подозрительный перевод солидные $1,4 млрд в крипте. Глава криптобиржи Bybit Бен Чжоу заявил в X (твиттере), что один из холодных кошельков Ethereum биржи был скомпрометирован."\
          "Хакеры обошли систему безопасности, подменив данные транзакции: при подписании все участники видели правильный адрес, но фактически подтверждали изменение смарт-контракта. Это позволило злоумышленникам вывести средства."\
          "Чжоу подчеркнул, что другие холодные кошельки Bybit остаются в безопасности"\
          "Мы уже расследуем произошедший инцидент. Средства пользователей в безопасности"\
          "сообщили в компании"
string2 = ("Хакеры взломали криптобиржу ByBit и украли 1,5 млрд долларов в монетах Ethereum. "
           "Информацию подтвердил СЕО биржи в соцсети Х. "
           "Хакеры обошли систему безопасности, подменив данные транзакции. "
           "Это позволило злоумышленникам вывести средства.")

def preprocess(text:str) -> str:
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    word_tokens = word_tokenize(text)
    stop_words = set(stopwords.words('russian'))
    filtered_text = [word for word in word_tokens if word not in stop_words]
    return " ".join(filtered_text)

preprocessed_string1 = preprocess(string1)
preprocessed_string2 = preprocess(string2)
print(string1)
print(preprocessed_string1)



tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform([string1, string2])

tf_idf_similarity = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])
print(tf_idf_similarity[0][0])

model = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")


if __name__ == '__main__':

    #
    # model = ElmoModel()
    # model.load("/Users/dinayatsuk/MyDigest/MyDigest/209.zip")
    #
    # embedding1 = get_sentence_embedding(string1)
    # embedding2 = get_sentence_embedding(string2)
    #
    # print(embedding1)
    # print(embedding2)

    import tensorflow as tf
    import tensorflow_hub as hub
    import numpy as np

    # Load the Universal Sentence Encoder model from TFHub.



    def get_sentence_embedding(sentence):
        # The model returns a tensor of shape (batch_size, embedding_dim)
        return model([sentence])[0].numpy()


    def cosine_similarity(vec1, vec2):
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


    # Example sentences.
    sentence1 = "The cat sat on the mat."
    sentence2 = "A cat was resting on the rug."

    # Get embeddings.
    emb1 = get_sentence_embedding(string1)
    emb2 = get_sentence_embedding(string2)

    # Calculate cosine similarity.
    similarity = cosine_similarity(emb1, emb2)
    print("Cosine similarity (USE):", similarity)
