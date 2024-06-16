import sys
import os
import json
import asyncio
from aiokafka import AIOKafkaConsumer
from pydub import AudioSegment
import whisper
from rake_nltk import Rake
import nltk
import torch

nltk.download('stopwords')
stop_words = set(nltk.corpus.stopwords.words('russian'))

# Загрузка модели Whisper
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
audio_model = whisper.load_model("large", device=device)

def convert_audio(video_path, output_path="converted_audio.wav"):
    audio = AudioSegment.from_file(video_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(output_path, format="wav")
    return output_path

def recognize_speech(audio_path):
    result = audio_model.transcribe(audio_path)
    return result['text']

def extract_audio_keywords(text):
    r = Rake(stopwords=stop_words, language="russian")
    r.extract_keywords_from_text(text)
    keywords = r.get_ranked_phrases()
    return keywords

async def process_audio_message(data, send_to_kafka, result_topic):
    video_url = data.get('video_link')
    if video_url:
        unique_video_filename = f"temp_audio.{os.path.basename(video_url).split('.')[-1]}"
        converted_audio_path = "converted_audio.wav"
        
        try:
            await download_file(video_url, unique_video_filename)
            converted_audio_path = convert_audio(unique_video_filename)
            text = recognize_speech(converted_audio_path)
            keywords = extract_audio_keywords(text)
            
            result_data = {
                "type": "audio",
                "video_link": video_url,
                "marks": keywords
            }
            await send_to_kafka(result_topic, result_data)
        finally:
            os.remove(unique_video_filename)
            os.remove(converted_audio_path)

async def send_to_kafka(topic, data):
    producer = AIOKafkaProducer(bootstrap_servers='localhost:29092')
    await producer.start()
    try:
        value = json.dumps(data).encode('utf-8')
        await producer.send_and_wait(topic, value)
    finally:
        await producer.stop()

async def download_file(url, dest):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(dest, 'wb') as f:
                    f.write(await response.read())
            else:
                raise Exception(f"Failed to download file from {url}")

async def consume():
    consumer = AIOKafkaConsumer('audio_topic', bootstrap_servers='localhost:29092', group_id="audio_group")
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            await process_audio_message(data, send_to_kafka, 'result_topic')
    except Exception as e:
        print(f"Kafka error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except Exception as e:
        print(f"Error running main loop: {e}")
