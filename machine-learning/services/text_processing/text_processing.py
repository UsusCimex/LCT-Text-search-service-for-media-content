from fastapi import FastAPI
from pydantic import BaseModel
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from keybert import KeyBERT
import asyncio
import json

app = FastAPI()
model = KeyBERT()

KAFKA_BROKER = 'localhost:9092'
TOPIC = 'text_topic'

producer = AIOKafkaProducer(loop=asyncio.get_event_loop(), bootstrap_servers=KAFKA_BROKER)
consumer = AIOKafkaConsumer(TOPIC, loop=asyncio.get_event_loop(), bootstrap_servers=KAFKA_BROKER, group_id="text_group")

class TextRequest(BaseModel):
    text: str

class TextResponse(BaseModel):
    type: str
    marks: dict

async def send_to_kafka(data: dict):
    await producer.start()
    try:
        value = json.dumps(data).encode('utf-8')
        await producer.send_and_wait(TOPIC, value)
    finally:
        await producer.stop()

@app.post("/process_text/", response_model=TextResponse)
async def process_text(request: TextRequest):
    keywords = model.extract_keywords(request.text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=5)
    marks = {kw[0] for kw in keywords}
    
    data = {
        "type": "text",
        "marks": marks
    }
    
    await send_to_kafka(data)
    
    return data

@app.on_event("startup")
async def startup_event():
    await consumer.start()
    asyncio.create_task(consume())

async def consume():
    async for msg in consumer:
        data = json.loads(msg.value.decode('utf-8'))
        print(f"Received message: {data}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
