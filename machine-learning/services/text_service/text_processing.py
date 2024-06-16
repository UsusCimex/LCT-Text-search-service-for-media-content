import sys
import asyncio
import json
from aiokafka import AIOKafkaConsumer
sys.path.append('..')
from kafka_utils import send_to_kafka
from keybert import KeyBERT

# Инициализация модели KeyBERT
text_model = KeyBERT()

def extract_text_keywords(text):
    keywords = text_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=5)
    return [kw[0] for kw in keywords]

async def process_text_message(data, send_to_kafka, result_topic):
    text = data.get('description')
    video_url = data.get('video_link')
    if text:
        keywords = extract_text_keywords(text)
        result_data = {
            "type": "text",
            "video_link": video_url,
            "marks": keywords
        }
        await send_to_kafka(result_topic, result_data)

async def consume():
    consumer = AIOKafkaConsumer('text_topic', bootstrap_servers='kafka:29092', group_id="text_group")
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            await process_text_message(data, send_to_kafka, 'result_topic')
    except Exception as e:
        print(f"Kafka error: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except Exception as e:
        print(f"Error running main loop: {e}")
