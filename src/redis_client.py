from redis import asyncio
from src.config import Config

redis_client = asyncio.from_url(
    Config.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)