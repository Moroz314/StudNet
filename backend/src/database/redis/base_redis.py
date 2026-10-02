import os
from dotenv import load_dotenv
import redis.asyncio as redis

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST") or "redis"
REDIS_PORT = os.getenv("REDIS_PORT") or "6379"
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

class RedisInit:
    def __init__(self):
        self.redis = redis.from_url(
            url=REDIS_URL,
            password=REDIS_PASSWORD,
            decode_responses=True
        )