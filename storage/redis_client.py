import os
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(REDIS_URL, decode_responses=False)
    # decode_responses=False, потому что мы будем хранить pickle-байты