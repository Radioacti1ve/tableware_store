import os
import json
import uuid
from app.redis_client import get_redis

DEFAULT_TTL = int(os.getenv("CACHE_TTL", 300))  # по умолчанию 5 минут

import uuid
import decimal

def make_json_serializable(obj):
    """
    Преобразует asyncpg.Record или dict с UUID/Decimal в сериализуемую структуру.
    """
    if isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]

    elif isinstance(obj, dict):
        return {
            k: (
                str(v) if isinstance(v, uuid.UUID)
                else float(v) if isinstance(v, decimal.Decimal)
                else v
            )
            for k, v in obj.items()
        }

    elif hasattr(obj, 'items'):
        return {
            k: (
                str(v) if isinstance(v, uuid.UUID)
                else float(v) if isinstance(v, decimal.Decimal)
                else v
            )
            for k, v in dict(obj).items()
        }

    elif isinstance(obj, uuid.UUID):
        return str(obj)

    elif isinstance(obj, decimal.Decimal):
        return float(obj)

    return obj

async def get_or_cache_json(key: str, fetch_fn, ttl: int = DEFAULT_TTL):
    """
    Универсальная функция получения данных из кеша или из БД:
    - Пытается получить значение по ключу `key` из Redis.
    - Если значение найдено — возвращает его.
    - Если нет — вызывает функцию `fetch_fn`, сохраняет результат в Redis с TTL.
    """
    try:
        r = await get_redis()
        cached = await r.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        print(f"Redis недоступен (get): {e}")

    data = await fetch_fn()
    serializable_data = make_json_serializable(data)

    try:
        r = await get_redis()
        print(f"[DEBUG] Сохраняем ключ в Redis: {key}")
        await r.set(key, json.dumps(serializable_data), ex=ttl)
    except Exception as e:
        print(f"Redis недоступен (set): {e}")

    return serializable_data


async def invalidate_cache(key: str):
    """
    Удаляет ключ из кеша Redis.
    Используется при обновлении данных (например, категорий, товаров).
    """
    r = await get_redis()
    await r.delete(key)