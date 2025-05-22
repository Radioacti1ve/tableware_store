import redis.asyncio as redis_lib
import os

redis = None

async def init_redis():
    """
    Создаёт глобальное подключение к Redis, используя URL из переменных окружения.
    Подключение сохраняется в переменной redis для повторного использования.
    """
    global redis
    redis = redis_lib.from_url(
        os.getenv("REDIS_URL", "redis://localhost"),
        decode_responses=True
    )

async def get_redis():
    """
    Используется в любом месте приложения, где нужно работать с Redis.
    """
    global redis
    if redis is None:
        raise ConnectionError("Redis не инициализирован или не подключен.")
    return redis