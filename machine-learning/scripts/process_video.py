import os
import pandas as pd
from video_processing import process_video_stream, download_video_stream, save_video_stream
from tensorflow.keras.applications.resnet50 import ResNet50
import requests  # Импортируем библиотеку requests

def process_videos(csv_path, output_file, input_shape=(224, 224), max_videos=10):
    model = ResNet50(weights='imagenet')
    videos_df = pd.read_csv(csv_path)

    # Создание/очистка выходного файла с явной кодировкой UTF-8
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('link,description,labels\n')

    for index, row in videos_df.iterrows():
        if index >= max_videos:
            break
        video_url = row['link']
        description = row['description']
        print(f"Processing {video_url}")
        
        # Сохранение видео на диск
        video_stream = download_video_stream(video_url)
        temp_video_path = f"temp_video_{index}.mp4"
        save_video_stream(video_stream, temp_video_path)
        
        # Обработка видео
        annotations = process_video_stream(temp_video_path, model, input_shape)
        labels = [f'{label} ({weight})' for label, weight in annotations.items()]
        
        # Добавление результатов в выходной файл с явной кодировкой UTF-8
        print(f'Found results: {labels}')
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f'"{video_url}","{description}","{labels}"\n')
        
        # Удаление временного файла
        os.remove(temp_video_path)

if __name__ == "__main__":
    csv_path = "../data/csv/videos.csv"
    output_file = "../data/annotations.csv"
    process_videos(csv_path, output_file, max_videos=10)
