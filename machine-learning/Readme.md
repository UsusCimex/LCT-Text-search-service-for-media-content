# Проект обработки видео

## Требования
- Python 3.8+
- FFmpeg

## Установка

1. Клонируйте репозиторий:
    ```bash
    git clone <URL репозитория>
    cd <имя репозитория>
    ```

2. Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

3. Установите FFmpeg:
    - На **Windows**: скачайте FFmpeg с [официального сайта](https://ffmpeg.org/download.html), разархивируйте и добавьте путь к папке `bin` в переменную окружения `PATH`.
    - На **Ubuntu**:
        ```bash
        sudo apt update
        sudo apt install ffmpeg
        ```
    - На **MacOS**:
        ```bash
        brew install ffmpeg
        ```

## Использование
Запустите скрипт:
```bash
python scripts/main.py
```

Убедитесь, что файл videos.csv находится в папке data/csv/ и содержит ссылки на видео для обработки. Файл videos.csv должен иметь следующую структуру:
```csv
link,description
http://example.com/video1.mp4,Description of video 1
http://example.com/video2.mp4,Description of video 2
...
```

После выполнения скрипта, результаты будут сохранены в файл data/combined_labels.csv, который будет иметь следующую структуру:
```csv
link,description,combined_labels
http://example.com/video1.mp4,Description of video 1,Keywords: keyword1 (weight1%), Labels: label1 (weight1%), ...
http://example.com/video2.mp4,Description of video 2,Keywords: keyword2 (weight2%), Labels: label2 (weight2%), ...
...
```