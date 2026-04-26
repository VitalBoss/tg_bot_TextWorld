import json
import os
from typing import Optional, List
from redis.asyncio import Redis

class SessionService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def create_session(self, user_id: int, game_path: str):
        """Сохраняем путь к игре и пустую историю."""
        await self.redis.set(f"game_path:{user_id}", game_path)
        await self.redis.set(f"history:{user_id}", json.dumps([]))

    async def get_session(self, user_id: int) -> tuple[Optional[str], List[str]]:
        """Возвращает (game_path, history) или (None, [])."""
        game_path = await self.redis.get(f"game_path:{user_id}")
        if game_path is None:
            return None, []
        game_path = game_path.decode("utf-8") if isinstance(game_path, bytes) else game_path
        history_raw = await self.redis.get(f"history:{user_id}")
        history = json.loads(history_raw) if history_raw else []
        return game_path, history

    async def save_history(self, user_id: int, history: List[str]):
        await self.redis.set(f"history:{user_id}", json.dumps(history))

    async def delete_session(self, user_id: int):
        game_path = await self.redis.get(f"game_path:{user_id}")
        if game_path:
            path = game_path.decode("utf-8") if isinstance(game_path, bytes) else game_path
            if os.path.exists(path):
                os.remove(path)
        await self.redis.delete(f"game_path:{user_id}", f"history:{user_id}")