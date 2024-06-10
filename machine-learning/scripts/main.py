import os
import pandas as pd
import logging
from tensorflow.keras.applications.resnet50 import ResNet50
from video_processing import process_video

# Подавление вывода TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('tensorflow').setLevel(logging.ERROR)

def process_video_links(input_csv, output_csv, max_videos=1, input_shape=(224, 224)):
    model = ResNet50(weights='imagenet')
    df = pd.read_csv(input_csv)
    processed_data = []

    for index, row in df.iterrows():
        if index >= max_videos:
            break
        video_url = row['link']
        description = row['description']

        combined_labels = process_video(video_url, index, model, input_shape)
        processed_data.append({'link': video_url, 'description': description, 'combined_labels': combined_labels})

    # Создание нового DataFrame с обработанными данными
    processed_df = pd.DataFrame(processed_data)
    processed_df.to_csv(output_csv, index=False)

if __name__ == "__main__":
    input_csv = "../data/csv/videos.csv"
    output_csv = "../data/combined_labels.csv"
    process_video_links(input_csv, output_csv, max_videos=5)
