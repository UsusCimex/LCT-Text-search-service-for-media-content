import os
import json
import asyncio
import aiohttp
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from pydub import AudioSegment
import whisper
from rake_nltk import Rake
import nltk

nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('russian'))

# Настройка Kafka
KAFKA_BROKER = 'localhost:9092'
AUDIO_TOPIC = 'audio_topic'
RESULT_TOPIC = 'result_topic'

loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=KAFKA_BROKER)
consumer = AIOKafkaConsumer(AUDIO_TOPIC, loop=loop, bootstrap_servers=KAFKA_BROKER, group_id="audio_group")

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

async def send_to_kafka(topic, data: dict):
    await producer.start()
    try:
        value = json.dumps(data).encode('utf-8')
        await producer.send_and_wait(topic, value)
    finally:
        await producer.stop()

async def download_audio(url, file_path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    f.write(await response.read())
                return file_path
            else:
                raise Exception(f"Failed to download audio. Status code: {response.status}")

async def consume():
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            audio_url = data.get('url')
            
            if audio_url:
                unique_audio_filename = f"temp_audio.{os.path.basename(audio_url).split('.')[-1]}"
                converted_audio_path = "converted_audio.wav"
                
                try:
                    await download_audio(audio_url, unique_audio_filename)
                    
                    converted_audio_path = convert_audio(unique_audio_filename)
                    text = recognize_speech(converted_audio_path)
                    keywords_with_weights = extract_keywords(text)
                    keywords = {kw[0] for kw in keywords_with_weights}
                    
                    result_data = {
                        "type": "audio",
                        "marks": keywords
                    }
                    
                    await send_to_kafka(RESULT_TOPIC, result_data)
                
                finally:
                    if os.path.exists(unique_audio_filename):
                        os.remove(unique_audio_filename)
                    if os.path.exists(converted_audio_path):
                        os.remove(converted_audio_path)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    loop.run_until_complete(consume())
