FROM python:3.8-slim

WORKDIR .

COPY requirements.txt .
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY audio_processor.py .
COPY ../kafka_utils.py .

CMD ["python", "audio_processor.py"]
