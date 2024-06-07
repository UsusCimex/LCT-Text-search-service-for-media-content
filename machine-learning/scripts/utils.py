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
