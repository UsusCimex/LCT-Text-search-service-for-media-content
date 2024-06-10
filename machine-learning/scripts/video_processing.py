import os
import numpy as np
import moviepy.editor as mp
from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.preprocessing import image
from utils import download_video_stream
from audio_processing import convert_audio, recognize_speech
from keyword_extraction import extract_keywords
import contextlib

def process_video_stream(video, model, input_shape):
    try:
        frames = []
        
        # Извлечение кадров из видео
        for frame in video.iter_frames(fps=1):  # Извлекаем один кадр в секунду
            # Изменение размера кадра до input_shape
            frame = image.array_to_img(frame)
            frame = frame.resize(input_shape)
            frame = img_to_array(frame)
            frames.append(frame)

        predictions = []
        
        # Обработка каждого кадра
        for frame in frames:
            # Преобразование кадра для модели
            img = np.expand_dims(frame, axis=0)
            img = preprocess_input(img)
            
            # Предсказание модели
            preds = model.predict(img, verbose=0)
            decoded_preds = decode_predictions(preds, top=3)[0]
            
            predictions.extend(decoded_preds)
        
        # Агрегация результатов
        result_dict = {}
        for pred in predictions:
            label = pred[1]
            confidence = pred[2]
            if label in result_dict:
                result_dict[label] += confidence
            else:
                result_dict[label] = confidence

        # Усреднение весов
        for label in result_dict:
            result_dict[label] /= len(frames)
        
        return result_dict

    except Exception as e:
        print(f"Ошибка при обработке видео потока: {e}")
        return {}

def process_video(video_url, index, model, input_shape):
    video = None
    audio_path = None
    video_path = None
    try:
        print(f"Обработка видео {index + 1}: {video_url}")

        # Загрузка видео в память
        video_stream = download_video_stream(video_url)
        video_path = f"video_{index}.mp4"
        with open(video_path, "wb") as f:
            f.write(video_stream.getbuffer())

        # Открытие видеофайла с помощью moviepy
        video = mp.VideoFileClip(video_path)

        # Извлечение аудио из видео
        audio_path = f"audio_{index}.wav"
        
        if video.audio is None:
            raise ValueError("Аудио дорожка отсутствует в видео")

        video.audio.write_audiofile(audio_path, verbose=False)
        
        # Проверка аудио файла
        if os.path.getsize(audio_path) == 0:
            raise ValueError("Извлеченное аудио пустое")

        # Преобразование аудио в текст
        converted_audio_path = convert_audio(audio_path)
        text = recognize_speech(converted_audio_path)
        print(f"Распознанный текст: {text}")

        # Извлечение ключевых слов из текста
        keywords_with_weights = extract_keywords(text)
        keywords = [f'{keyword} ({weight:.2f}%)' for keyword, weight in keywords_with_weights]
        print(f"Ключевые слова: {keywords}")

        # Обработка видео для извлечения меток
        annotations = process_video_stream(video, model, input_shape)
        if not annotations:
            raise ValueError("Аннотации не получены или пусты")
        
        labels = [f'{label} ({weight:.2f}%)' for label, weight in annotations.items()]

        # Объединение ключевых слов и меток
        combined_labels = f"Keywords: {', '.join(keywords)}, Labels: {', '.join(labels)}"
        print(f"Комбинированные метки: {combined_labels}")

        return combined_labels
    except Exception as e:
        print(f"Ошибка при обработке видео {video_url}: {e}")
        return f"Ошибка при обработке видео: {e}"
    finally:
        # Закрытие видеофайла и удаление временных файлов
        try:
            if video:
                video.reader.close()
                if video.audio:
                    video.audio.reader.close_proc()
        except Exception as e:
            print(f"Ошибка при закрытии ресурсов видео: {e}")

        for path in [video_path, audio_path, "converted_audio.wav"]:
            if path and os.path.exists(path):
                with contextlib.suppress(PermissionError):
                    os.remove(path)
