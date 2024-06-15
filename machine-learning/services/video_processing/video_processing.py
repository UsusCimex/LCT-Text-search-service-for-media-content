import os
import json
import asyncio
import aiohttp
import numpy as np
from PIL import Image
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import moviepy.editor as mp
from tensorflow.keras.applications.efficientnet import EfficientNetB7, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
import tensorflow as tf

# Настройка GPU
physical_devices = tf.config.list_physical_devices('GPU')
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

# Настройка Kafka
KAFKA_BROKER = 'localhost:9092'
VIDEO_TOPIC = 'video_topic'
RESULT_TOPIC = 'result_topic'

loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=KAFKA_BROKER)
consumer = AIOKafkaConsumer(VIDEO_TOPIC, loop=loop, bootstrap_servers=KAFKA_BROKER, group_id="video_group")

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

    result_dict = {}
    for pred in predictions:
        label = pred[1]
        confidence = pred[2]
        if label in result_dict:
            result_dict[label] += confidence
        else:
            result_dict[label] = confidence

    for label in result_dict:
        result_dict[label] /= len(frames)

    sorted_result = dict(sorted(result_dict.items(), key=lambda item: item[1], reverse=True))
    res = [sr[0] for sr in sorted_result.items()]
    return res

async def send_to_kafka(topic, data: dict):
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

async def consume():
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            video_url = data.get('url')
            
            if video_url:
                video_file_path = f"temp/{os.path.basename(video_url)}"
                await download_video(video_url, video_file_path)
                
                video = mp.VideoFileClip(video_file_path)
                result_dict = process_video_stream(video, input_shape=(224, 224))
                
                result_data = {
                    "type": "video",
                    "marks": result_dict
                }
                
                await send_to_kafka(RESULT_TOPIC, result_data)
                
                os.remove(video_file_path)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    loop.run_until_complete(consume())
