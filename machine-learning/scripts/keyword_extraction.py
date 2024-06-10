import nltk
from rake_nltk import Rake

# Загрузка стоп-слов
nltk.download('stopwords', quiet=True)
stop_words = set(nltk.corpus.stopwords.words('russian'))

def extract_keywords(text):
    try:
        # Инициализация RAKE с использованием русских стоп-слов
        r = Rake(stopwords=stop_words, language="russian")
        r.extract_keywords_from_text(text)
        keywords = r.get_ranked_phrases_with_scores()
        print(f"Сырые ключевые слова: {keywords}")

        # Извлечение ключевых слов с оценками
        total_score = sum(score for score, keyword in keywords)
        keywords_with_weights = [(keyword, score / total_score * 100) for score, keyword in keywords[:10]]

        return keywords_with_weights
    except Exception as e:
        print(f"Ошибка при извлечении ключевых слов: {e}")
        return []
