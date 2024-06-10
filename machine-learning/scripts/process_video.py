import os
import pandas as pd
from video_processing import process_video_stream, download_video_stream, save_video_stream
from tensorflow.keras.applications.resnet50 import ResNet50
import requests  # Импортируем библиотеку requests

def process_video(video_url, index, model, input_shape):
    try:
        print(f"Обработка видео {index + 1}: {video_url}")

        # Загрузка видео
        video_stream = download_video_stream(video_url)
        video_path = f"video_{index}.mp4"
        with open(video_path, "wb") as f:
            f.write(video_stream.getbuffer())

        # Проверка, что видео файл сохранен
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видео не сохранено: {video_path}")

        # Извлечение аудио из видео
        audio_path = f"audio_{index}.wav"
        video = mp.VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path)
        video.close()

        # Проверка аудио файла
        if os.path.getsize(audio_path) == 0:
            raise ValueError("Извлеченное аудио пустое")

        # Преобразование аудио в текст
        converted_audio_path = convert_audio(audio_path)
        text = recognize_speech(converted_audio_path)
        print(f"Распознанный текст: {text}")

        # Извлечение ключевых слов из текста
        keywords = extract_keywords(text)
        print(f"Ключевые слова: {keywords}")

        # Обработка видео для извлечения меток
        annotations = process_video_stream(video_path, model, input_shape)
        if not annotations:
            raise ValueError("Аннотации не получены или пусты")
        
        labels = [f'{label} ({weight})' for label, weight in annotations.items()]

        # Объединение ключевых слов и меток
        combined_labels = f"Keywords: {keywords}, Labels: {', '.join(labels)}"
        print(f"Комбинированные метки: {combined_labels}")

        return combined_labels
    except Exception as e:
        print(f"Ошибка при обработке видео {video_url}: {e}")
        return f"Ошибка при обработке видео: {e}"
    finally:
        # Удаление временных файлов
        for path in [video_path, audio_path, "converted_audio.wav"]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except PermissionError as e:
                print(f"Ошибка при удалении файла {path}: {e}")

if __name__ == "__main__":
    csv_path = "../data/csv/videos.csv"
    output_file = "../data/annotations.csv"
    process_videos(csv_path, output_file, max_videos=10)
