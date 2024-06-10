import os
from pydub import AudioSegment
import whisper

def convert_audio(audio_path, output_path="converted_audio.wav"):
    try:
        audio = AudioSegment.from_wav(audio_path)
        audio = audio.set_frame_rate(16000)
        audio.export(output_path, format="wav")
        return output_path
    except Exception as e:
        raise RuntimeError(f"Ошибка при конвертации аудио: {e}")

def recognize_speech(audio_path):
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result['text']
    except Exception as e:
        raise RuntimeError(f"Ошибка при распознавании речи: {e}")
