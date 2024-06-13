from fastapi import FastAPI, UploadFile, File, HTTPException
from tensorflow.keras.applications.efficientnet import EfficientNetB7
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.efficientnet import preprocess_input, decode_predictions
import numpy as np
import moviepy.editor as mp
import os
import contextlib
from typing import List
from pydantic import BaseModel
import base64
from io import BytesIO
from PIL import Image
import concurrent.futures
import aiohttp
import asyncio
import uuid

app = FastAPI()

model = EfficientNetB7(weights='imagenet')

class ImageData(BaseModel):
    images: List[str]  # Base64 encoded images

class VideoURLData(BaseModel):
    url: str

def decode_base64_image(data: str) -> Image.Image:
    image_data = base64.b64decode(data)
    image = Image.open(BytesIO(image_data))
    return image

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

def process_images(images: List[str], model, input_shape):
    try:
        frames = [decode_base64_image(img_str) for img_str in images]

        predictions = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(process_frame, frame, input_shape): frame for frame in frames}
            for future in concurrent.futures.as_completed(futures):
                img_array = future.result()
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

        return sorted_result
    except Exception as e:
        return f"Ошибка при обработке изображений: {e}"

def process_video_stream(video, input_shape, frame_interval=0.5):
    try:
        frames = [Image.fromarray(frame).resize(input_shape) for frame in video.iter_frames(fps=1/frame_interval)]

        predictions = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(process_frame, frame, input_shape): frame for frame in frames}
            for future in concurrent.futures.as_completed(futures):
                img_array = future.result()
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

        return sorted_result
    except Exception as e:
        return f"Ошибка при обработке видео потока: {e}"

async def download_video(url: str, filename: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail="Ошибка при загрузке видео по URL")
            with open(filename, 'wb') as f:
                f.write(await response.read())

@app.post("/process_images/")
async def process_images_endpoint(data: ImageData, input_shape=(600, 600)):
    try:
        result_dict = process_images(data.images, model, input_shape)
        return {"marks": result_dict}
    except Exception as e:
        return {"error": str(e)}

@app.post("/process_video/")
async def process_video(file: UploadFile = File(...), input_shape=(600, 600)):
    unique_filename = f"temp/{uuid.uuid4()}.mp4"
    try:
        with open(unique_filename, "wb") as f:
            f.write(await file.read())

        video = mp.VideoFileClip(unique_filename)
        result_dict = process_video_stream(video, input_shape)
        
        return {"marks": result_dict}
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            if video:
                video.reader.close()
                if video.audio:
                    video.audio.reader.close_proc()
        except Exception as e:
            print(f"Ошибка при закрытии ресурсов видео: {e}")

        if os.path.exists(unique_filename):
            with contextlib.suppress(PermissionError):
                os.remove(unique_filename)

@app.post("/process_video_url/")
async def process_video_url(data: VideoURLData, input_shape=(600, 600)):
    unique_filename = f"temp/{uuid.uuid4()}.mp4"
    try:
        await download_video(data.url, unique_filename)

        video = mp.VideoFileClip(unique_filename)
        result_dict = process_video_stream(video, input_shape)
        
        return {"marks": result_dict}
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            if video:
                video.reader.close()
                if video.audio:
                    video.audio.reader.close_proc()
        except Exception as e:
            print(f"Ошибка при закрытии ресурсов видео: {e}")

        if os.path.exists(unique_filename):
            with contextlib.suppress(PermissionError):
                os.remove(unique_filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
