import sys
import os
import json
import asyncio
import aiohttp
import numpy as np
from PIL import Image
from aiokafka import AIOKafkaConsumer
sys.path.append('..')
from kafka_utils import send_to_kafka, download_file
from tensorflow.keras.applications.efficientnet import EfficientNetB7, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
import tensorflow as tf
import moviepy.editor as mp

# Настройка GPU
physical_devices = tf.config.list_physical_devices('GPU')
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

# Настройка Kafka
KAFKA_BROKER = 'kafka:29092'
VIDEO_TOPIC = 'video_topic'
RESULT_TOPIC = 'result_topic'

# Загрузка модели
model = EfficientNetB7(weights='imagenet')

def process_frame(frame, input_shape):
    img = frame.resize(input_shape)
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    return img_array

def predict_with_model(img_array):
    preds = model.predict(img_array, verbose=0)
    decoded_preds = decode_predictions(preds, top=3)[0]
    return decoded_preds

def process_video_stream(video, input_shape, frame_interval=0.5):
    frames = [Image.fromarray(frame).resize(input_shape) for frame in video.iter_frames(fps=1/frame_interval)]

    predictions = []
    for frame in frames:
        img_array = process_frame(frame, input_shape)
        decoded_preds = predict_with_model(img_array)
        predictions.extend(decoded_preds)

    labels = {pred[1] for pred in predictions}
    return list(labels)

async def send_to_kafka(topic, data: dict):
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKER)
    await producer.start()
    try:
        value = json.dumps(data).encode('utf-8')
        await producer.send_and_wait(topic, value)
    finally:
        await producer.stop()

async def download_video(url, file_path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    f.write(await response.read())
                return file_path
            else:
                raise Exception(f"Failed to download video. Status code: {response.status}")

async def process_video_message(data, send_to_kafka, result_topic):
    video_url = data.get('video_link')
    if video_url:
        video_file_path = f"temp/{os.path.basename(video_url)}"
        await download_video(video_url, video_file_path)
        
        video = mp.VideoFileClip(video_file_path)
        labels = process_video_stream(video, input_shape=(224, 224))
        
        result_data = {
            "type": "video",
            "video_link": video_url,
            "marks": labels
        }
        
        await send_to_kafka(result_topic, result_data)
        
        os.remove(video_file_path)

async def consume():
    consumer = AIOKafkaConsumer(VIDEO_TOPIC, bootstrap_servers=KAFKA_BROKER, group_id="video_group")
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            await process_video_message(data, send_to_kafka, RESULT_TOPIC)
    except Exception as e:
        print(f"Kafka error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except Exception as e:
        print(f"Error running main loop: {e}")
