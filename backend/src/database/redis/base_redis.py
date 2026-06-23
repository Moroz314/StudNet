import os
from dotenv import load_dotenv
import redis.asyncio as redis

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

class RedisInit:
    def __init__(self):
        self.redis = redis.from_url(
            url=REDIS_URL,
            password=REDIS_PASSWORD,
            decode_responses=True
        )