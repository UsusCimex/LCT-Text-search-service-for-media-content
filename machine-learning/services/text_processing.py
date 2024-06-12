from fastapi import FastAPI
from pydantic import BaseModel
from rake_nltk import Rake
import nltk

# Загрузка стоп-слов
nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('russian'))

app = FastAPI()

class TextRequest(BaseModel):
    text: str

def extract_keywords(text):
    try:
        # Инициализация RAKE с использованием русских стоп-слов
        r = Rake(stopwords=stop_words, language="russian")
        r.extract_keywords_from_text(text)
        keywords = r.get_ranked_phrases_with_scores()
        
        # Извлечение ключевых слов с оценками
        total_score = sum(score for score, keyword in keywords)
        keywords_with_weights = [(keyword, score / total_score * 100) for score, keyword in keywords[:10]]
        
        return keywords_with_weights
    except Exception as e:
        return f"Ошибка при извлечении ключевых слов: {e}"

@app.post("/process_text/")
async def process_text(request: TextRequest):
    print("Processing: " + request.text[:10] + "...")
    try:
        text = request.text
        keywords_with_weights = extract_keywords(text)
        keywords = [f'{keyword} ({weight:.2f}%)' for keyword, weight in keywords_with_weights]
        return {"marks": keywords}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
