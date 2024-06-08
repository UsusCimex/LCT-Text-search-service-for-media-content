import cv2
import numpy as np
import requests
from io import BytesIO  # Добавим этот импорт
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
from utils import download_video_stream, save_video_stream, translate_to_russian

def extract_frames(video_path, num_frames=10):
    vidcap = cv2.VideoCapture(video_path)
    total_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = total_frames // num_frames
    frames = []

    for i in range(num_frames):
        vidcap.set(cv2.CAP_PROP_POS_FRAMES, i * frame_interval)
        success, image = vidcap.read()
        if success:
            frames.append(image)
        else:
            break

    vidcap.release()
    return frames

def process_video_stream(video_path, model, input_shape=(224, 224), num_frames=10, prediction_threshold=0.5):
    frames = extract_frames(video_path, num_frames)
    annotations = {}
    
    for image in frames:
        image_resized = cv2.resize(image, input_shape)
        image_array = img_to_array(image_resized)
        image_array = preprocess_input(image_array)
        image_array = np.expand_dims(image_array, axis=0)
        
        preds = model.predict(image_array, verbose=0)  # Установка verbose=0 для отключения вывода прогресса
        decoded_preds = decode_predictions(preds, top=5)[0]  # Top 5 predictions
        for pred in decoded_preds:
            label = pred[1]
            probability = round(pred[2], 4)
            if probability > prediction_threshold:
                if label not in annotations or annotations[label] < probability:
                    annotations[label] = probability

    # Перевод меток на русский язык
    translated_annotations = {translate_to_russian(label): prob for label, prob in annotations.items()}
    return translated_annotations

def download_video_stream(url):
    response = requests.get(url, stream=True)
    video_stream = BytesIO(response.content)
    return video_stream

def save_video_stream(video_stream, output_path):
    with open(output_path, 'wb') as f:
        f.write(video_stream.read())