from fastapi import FastAPI, UploadFile, File
from pydub import AudioSegment
import whisper
from rake_nltk import Rake
import nltk
import os

nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('russian'))

app = FastAPI()

def convert_audio(audio_path, output_path="converted_audio.wav"):
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)
    audio.export(output_path, format="wav")
    return output_path

def recognize_speech(audio_path):
    model = whisper.load_model("large")
    result = model.transcribe(audio_path)
    return result['text']

def extract_keywords(text):
    r = Rake(stopwords=stop_words, language="russian")
    r.extract_keywords_from_text(text)
    keywords = r.get_ranked_phrases_with_scores()
    total_score = sum(score for score, keyword in keywords)
    keywords_with_weights = [(keyword, score / total_score * 100) for score, keyword in keywords[:10]]
    return keywords_with_weights

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    print("Processing: " + file.filename)
    try:
        audio_path = f"temp_audio.{file.filename.split('.')[-1]}"
        with open(audio_path, "wb") as f:
            f.write(await file.read())

        converted_audio_path = convert_audio(audio_path)
        text = recognize_speech(converted_audio_path)

        keywords_with_weights = extract_keywords(text)
        keywords = {keyword: weight for keyword, weight in keywords_with_weights}

        os.remove(audio_path)
        os.remove(converted_audio_path)

        return {"marks": keywords}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
