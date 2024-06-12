from fastapi import FastAPI, UploadFile, File
from tensorflow.keras.applications.resnet50 import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
import numpy as np
import moviepy.editor as mp
import os
import contextlib

app = FastAPI()

model = ResNet50(weights='imagenet')

def process_video_stream(video, model, input_shape):
    try:
        frames = []

        # Извлечение кадров из видео
        for frame in video.iter_frames(fps=1):  # Извлекаем один кадр в секунду
            frame = image.array_to_img(frame)
            frame = frame.resize(input_shape)
            frame = image.img_to_array(frame)
            frames.append(frame)

        predictions = []
        for frame in frames:
            img = np.expand_dims(frame, axis=0)
            img = preprocess_input(img)
            preds = model.predict(img, verbose=0)
            decoded_preds = decode_predictions(preds, top=3)[0]
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

        return result_dict
    except Exception as e:
        return f"Ошибка при обработке видео потока: {e}"

@app.post("/process_video/")
async def process_video(file: UploadFile = File(...), input_shape=(224, 224)):
    print("Processing: " + file.filename)
    video_path = "temp_video.mp4"
    try:
        with open(video_path, "wb") as f:
            f.write(await file.read())

        video = mp.VideoFileClip(video_path)
        result_dict = process_video_stream(video, model, input_shape)
        
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

        if os.path.exists(video_path):
            with contextlib.suppress(PermissionError):
                os.remove(video_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
