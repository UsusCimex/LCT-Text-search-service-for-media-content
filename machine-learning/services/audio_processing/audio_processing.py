from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from pydub import AudioSegment
import whisper
from rake_nltk import Rake
import nltk
import os
import asyncio
import json

nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('russian'))

app = FastAPI()

KAFKA_BROKER = 'localhost:9092'
TOPIC = 'audio_topic'

loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=KAFKA_BROKER)
consumer = AIOKafkaConsumer(TOPIC, loop=loop, bootstrap_servers=KAFKA_BROKER, group_id="audio_group")

class AudioResponse(BaseModel):
    type: str
    marks: dict

def convert_audio(audio_path, output_path="converted_audio.wav"):
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)
    audio.export(output_path, format="wav")
    return output_path

def recognize_speech(audio_path):
    model = whisper.load_model("large", device="cuda")  # Указание на использование GPU
    result = model.transcribe(audio_path)
    return result['text']

def extract_keywords(text):
    r = Rake(stopwords=stop_words, language="russian")
    r.extract_keywords_from_text(text)
    keywords = r.get_ranked_phrases_with_scores()
    total_score = sum(score for score, keyword in keywords)
    keywords_with_weights = [(keyword, score / total_score * 100) for score, keyword in keywords[:10]]
    return keywords_with_weights

async def send_to_kafka(data: dict):
    await producer.start()
    try:
        value = json.dumps(data).encode('utf-8')
        await producer.send_and_wait(TOPIC, value)
    finally:
        await producer.stop()

@app.post("/process_audio/", response_model=AudioResponse)
async def process_audio(file: UploadFile = File(...)):
    unique_audio_filename = f"temp_audio.{file.filename.split('.')[-1]}"
    converted_audio_path = "converted_audio.wav"
    try:
        with open(unique_audio_filename, "wb") as f:
            f.write(await file.read())

        converted_audio_path = convert_audio(unique_audio_filename)
        text = recognize_speech(converted_audio_path)

        keywords_with_weights = extract_keywords(text)
        keywords = {kw[0] for kw in keywords_with_weights}

        data = {
            "type": "audio",
            "marks": keywords
        }
        
        await send_to_kafka(data)
        
        return data
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(unique_audio_filename):
            os.remove(unique_audio_filename)
        if os.path.exists(converted_audio_path):
            os.remove(converted_audio_path)

@app.on_event("startup")
async def startup_event():
    await consumer.start()
    asyncio.create_task(consume())

async def consume():
    async for msg in consumer:
        data = json.loads(msg.value.decode('utf-8'))
        print(f"Received message: {data}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
