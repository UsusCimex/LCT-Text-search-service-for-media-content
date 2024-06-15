from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import moviepy.editor as mp
import os
import asyncio
import json
import numpy as np
from PIL import Image
from tensorflow.keras.applications.efficientnet import EfficientNetB7, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
import tensorflow as tf

physical_devices = tf.config.list_physical_devices('GPU')
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

app = FastAPI()

KAFKA_BROKER = 'localhost:9092'
TOPIC = 'video_topic'

loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=KAFKA_BROKER)
consumer = AIOKafkaConsumer(TOPIC, loop=loop, bootstrap_servers=KAFKA_BROKER, group_id="video_group")

model = EfficientNetB7(weights='imagenet')

class VideoResponse(BaseModel):
    type: str
    marks: dict

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
    res = [sr[0] for sr in sorted_result]
    return res

async def send_to_kafka(data: dict):
    await producer.start()
    try:
        value = json.dumps(data).encode('utf-8')
        await producer.send_and_wait(TOPIC, value)
    finally:
        await producer.stop()

@app.post("/process_video/", response_model=VideoResponse)
async def process_video(file: UploadFile = File(...)):
    unique_filename = f"temp/{file.filename.split('/')[-1]}"
    try:
        with open(unique_filename, "wb") as f:
            f.write(await file.read())

        video = mp.VideoFileClip(unique_filename)
        result_dict = process_video_stream(video, input_shape=(224, 224))
        
        data = {
            "type": "video",
            "marks": result_dict
        }
        
        await send_to_kafka(data)
        
        return data
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(unique_filename):
            os.remove(unique_filename)

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
    uvicorn.run(app, host="0.0.0.0", port=8001)
