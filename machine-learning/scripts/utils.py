import requests
from io import BytesIO
from googletrans import Translator

def download_video_stream(url):
    response = requests.get(url, stream=True)
    video_stream = BytesIO(response.content)
    return video_stream

def save_video_stream(video_stream, output_path):
    with open(output_path, 'wb') as f:
        f.write(video_stream.read())

def translate_to_russian(text):
    translator = Translator()
    translated = translator.translate(text, dest='ru')
    return translated.text

def extract_audio_from_video(video_path, audio_path):
    video = mp.VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_path)

def audio_to_text(audio_path):
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export("converted_audio.wav", format="wav")
    
    recognizer = sr.Recognizer()
    with sr.AudioFile("converted_audio.wav") as source:
        audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language="ru-RU")
    return text