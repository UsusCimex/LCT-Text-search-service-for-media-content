FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    wget \
    && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["python", "audio_processor.py"]
