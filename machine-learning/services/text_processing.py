from fastapi import FastAPI
from pydantic import BaseModel
from keybert import KeyBERT
from typing import Dict

app = FastAPI()
model = KeyBERT()

class TextRequest(BaseModel):
    text: str

class KeywordResponse(BaseModel):
    marks: Dict[str, float]

@app.post("/process_text/", response_model=KeywordResponse)
async def process_text(request: TextRequest):
    # Ограничение количества возвращаемых ключевых слов для ускорения обработки
    keywords = model.extract_keywords(request.text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=5)
    return {"marks": {kw[0]: kw[1] for kw in keywords}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
