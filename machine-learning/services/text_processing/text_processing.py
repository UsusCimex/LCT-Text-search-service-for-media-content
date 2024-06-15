import asyncio
import json
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from keybert import KeyBERT

# Настройка Kafka
KAFKA_BROKER = 'localhost:9092'
TEXT_TOPIC = 'text_topic'
RESULT_TOPIC = 'result_topic'

# Создание экземпляров Kafka Producer и Consumer
loop = asyncio.get_event_loop()
producer = AIOKafkaProducer(loop=loop, bootstrap_servers=KAFKA_BROKER)
consumer = AIOKafkaConsumer(TEXT_TOPIC, loop=loop, bootstrap_servers=KAFKA_BROKER, group_id="text_group")

# Инициализация модели KeyBERT
model = KeyBERT()

async def send_to_kafka(topic, data: dict):
    await producer.start()
    try:
        value = json.dumps(data).encode('utf-8')
        await producer.send_and_wait(topic, value)
    finally:
        await producer.stop()

async def process_text(text: str):
    keywords = model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=5)
    marks = {kw[0] for kw in keywords}
    
    data = {
        "type": "text",
        "description": text,
        "marks": marks
    }
    
    await send_to_kafka(RESULT_TOPIC, data)

async def consume():
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            text = data.get('description')
            
            if text:
                await process_text(text)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    loop.run_until_complete(consume())
