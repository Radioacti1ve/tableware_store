import os
from app.redis_client import get_redis
import json
from datetime import datetime
from quart import request

AUTH_TOKEN_TTL = int(os.getenv("AUTH_TOKEN_TTL", 3600))

async def store_token(token: str, user_id: str, ttl: int = 1800):
    r = await get_redis()
    
    # Формируем запись логов с IP и временем
    log_entry = {
        "token": token,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr)
    }
    await r.lpush(f"session_log:{user_id}", json.dumps(log_entry))
    await r.ltrim(f"session_log:{user_id}", 0, 9)
    
    # Сохраняем сам токен с привязкой к user_id и временем жизни
    await r.set(f"auth_token:{token}", user_id, ex=ttl)

async def get_user_by_token(token: str) -> str | None:
    r = await get_redis()
    return await r.get(f"auth_token:{token}")

async def delete_token(token: str):
    r = await get_redis()
    await r.delete(f"auth_token:{token}")