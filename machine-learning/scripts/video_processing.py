import cv2
import numpy as np
import requests
from io import BytesIO
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
from scene_detection import is_scene_change
from utils import download_video_stream, save_video_stream, translate_to_russian

def process_video_stream(video_path, model, input_shape=(224, 224), threshold=0.7):
    annotations = set()
    vidcap = cv2.VideoCapture(video_path)
    success, prev_image = vidcap.read()

    if success:
        prev_image_resized = cv2.resize(prev_image, input_shape)
        prev_hist = cv2.calcHist([prev_image_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(prev_hist, prev_hist)

    while success:
        success, curr_image = vidcap.read()
        if not success:
            break
        
        curr_image_resized = cv2.resize(curr_image, input_shape)
        curr_hist = cv2.calcHist([curr_image_resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(curr_hist, curr_hist)
        
        if is_scene_change(prev_hist, curr_hist, threshold):
            image_array = img_to_array(curr_image_resized)
            image_array = preprocess_input(image_array)
            image_array = np.expand_dims(image_array, axis=0)
            
            preds = model.predict(image_array, verbose=0)  # Установка verbose=0 для отключения вывода прогресса
            decoded_preds = decode_predictions(preds, top=5)[0]  # Top 5 predictions
            labels_with_weights = [(translate_to_russian(pred[1]), round(pred[2], 4)) for pred in decoded_preds]
            annotations.update(labels_with_weights)
            
            prev_hist = curr_hist

    vidcap.release()
    return annotations

def download_video_stream(url):
    response = requests.get(url, stream=True)
    video_stream = BytesIO(response.content)
    return video_stream

def save_video_stream(video_stream, output_path):
    with open(output_path, 'wb') as f:
        f.write(video_stream.read())
