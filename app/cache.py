import redis
import json
import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(
        REDIS_URL, decode_responses=True, socket_connect_timeout=2
    )
    redis_client.ping()
except Exception as e:
    logger.warning(f"Failed to connect to Redis: {e}")
    redis_client = None


def get_cache(key: str):
    if redis_client:
        try:
            val = redis_client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
    return None


def set_cache(key: str, data: dict, expire: int = 300):
    if redis_client:
        try:
            redis_client.setex(key, expire, json.dumps(data))
        except Exception as e:
            logger.warning(f"Redis set error: {e}")


def invalidate_cache(pattern: str):
    if redis_client:
        try:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis invalidate error: {e}")
