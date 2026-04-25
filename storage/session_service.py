import pickle
import os
from typing import Optional
from redis.asyncio import Redis
from game.world import GameSession

class SessionService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def create_session(self, user_id: int, game_path: str) -> GameSession:
        session = GameSession(game_path)
        # Сохраняем сессию в Redis
        await self._save(user_id, session)
        # Сохраняем путь к файлу игры отдельно, чтобы потом удалить
        await self.redis.set(f"game_path:{user_id}", game_path)
        return session

    async def get_session(self, user_id: int) -> Optional[GameSession]:
        data = await self.redis.get(f"session:{user_id}")
        if data is None:
            return None
        return pickle.loads(data)

    async def update_session(self, user_id: int, session: GameSession):
        await self._save(user_id, session)

    async def delete_session(self, user_id: int):
        # Удаляем файл игры, если он ещё существует
        game_path = await self.redis.get(f"game_path:{user_id}")
        if game_path:
            path = game_path.decode("utf-8") if isinstance(game_path, bytes) else game_path
            if os.path.exists(path):
                os.remove(path)
        # Удаляем ключи из Redis
        await self.redis.delete(f"session:{user_id}", f"game_path:{user_id}")

    async def _save(self, user_id: int, session: GameSession):
        # Сериализуем сессию с помощью pickle
        await self.redis.set(f"session:{user_id}", pickle.dumps(session))