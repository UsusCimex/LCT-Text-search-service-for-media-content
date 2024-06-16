import aiohttp
import json
from aiokafka import AIOKafkaProducer

async def send_to_kafka(topic, data):
    producer = AIOKafkaProducer(bootstrap_servers='localhost:29092')
    await producer.start()
    try:
        value = json.dumps(data).encode('utf-8')
        await producer.send_and_wait(topic, value)
    finally:
        await producer.stop()

async def download_file(url, dest):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(dest, 'wb') as f:
                    f.write(await response.read())
            else:
                raise Exception(f"Failed to download file from {url}")
