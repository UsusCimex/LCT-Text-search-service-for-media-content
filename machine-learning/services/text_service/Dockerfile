FROM python:3.8-slim

WORKDIR .

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY text_processing.py .

CMD ["python", "text_processing.py"]
