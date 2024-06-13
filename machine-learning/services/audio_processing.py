from fastapi import FastAPI, UploadFile, File, HTTPException
from pydub import AudioSegment
import whisper
from rake_nltk import Rake
import nltk
import os
from typing import List
from pydantic import BaseModel
import moviepy.editor as mp
import aiohttp
import uuid
import contextlib

nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('russian'))

app = FastAPI()

class VideoURLData(BaseModel):
    url: str

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

async def download_video(url: str, filename: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail="Ошибка при загрузке видео по URL")
            with open(filename, 'wb') as f:
                f.write(await response.read())

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    unique_audio_filename = f"temp_audio.{file.filename.split('.')[-1]}"
    converted_audio_path = "converted_audio.wav"
    try:
        with open(unique_audio_filename, "wb") as f:
            f.write(await file.read())

        converted_audio_path = convert_audio(unique_audio_filename)
        text = recognize_speech(converted_audio_path)

        keywords_with_weights = extract_keywords(text)
        keywords = {keyword: weight for keyword, weight in keywords_with_weights}

        return {"marks": keywords}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(unique_audio_filename):
            with contextlib.suppress(PermissionError, FileNotFoundError):
                os.remove(unique_audio_filename)
        if os.path.exists(converted_audio_path):
            with contextlib.suppress(PermissionError, FileNotFoundError):
                os.remove(converted_audio_path)

@app.post("/process_video_url/")
async def process_video_url(data: VideoURLData):
    unique_video_filename = f"{uuid.uuid4()}.mp4"
    unique_audio_filename = f"{uuid.uuid4()}.wav"
    converted_audio_path = "converted_audio.wav"
    try:
        await download_video(data.url, unique_video_filename)

        video = mp.VideoFileClip(unique_video_filename)
        video.audio.write_audiofile(unique_audio_filename, codec='pcm_s16le')
        
        # Ensure video resources are released before deleting the file
        video.reader.close()
        if video.audio:
            video.audio.reader.close_proc()

        converted_audio_path = convert_audio(unique_audio_filename)
        text = recognize_speech(converted_audio_path)

        keywords_with_weights = extract_keywords(text)
        keywords = {keyword: weight for keyword, weight in keywords_with_weights}

        return {"marks": keywords}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(unique_video_filename):
            with contextlib.suppress(PermissionError, FileNotFoundError):
                os.remove(unique_video_filename)
        if os.path.exists(unique_audio_filename):
            with contextlib.suppress(PermissionError, FileNotFoundError):
                os.remove(unique_audio_filename)
        if os.path.exists(converted_audio_path):
            with contextlib.suppress(PermissionError, FileNotFoundError):
                os.remove(converted_audio_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
