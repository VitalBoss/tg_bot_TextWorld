import asyncpg

class SessionLogger:
    def __init__(self, pool):
        self.pool = pool

    async def start_session(self, user_id: int, game_path: str) -> str:
        """Создаёт запись о новой игровой сессии и возвращает её UUID."""
        async with self.pool.acquire() as conn:
            # Если пользователь не зарегистрирован, создаём запись
            await conn.execute('''
                INSERT INTO users (telegram_id, username) VALUES ($1, 'player')
                ON CONFLICT (telegram_id) DO NOTHING
            ''', user_id)
            user_db_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', user_id)
            session_id = await conn.fetchval('''
                INSERT INTO game_sessions (user_id, game_file_path) VALUES ($1, $2)
                RETURNING id
            ''', user_db_id, game_path)
            return str(session_id)

    async def log_move(self, session_id: str, move_number: int, command: str, feedback: str, admissible_commands: list):
        """Записывает один ход."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO game_moves (session_id, move_number, command, feedback, admissible_commands)
                VALUES ($1, $2, $3, $4, $5)
            ''', session_id, move_number, command, feedback, admissible_commands)

    async def finish_session(self, session_id: str):
        """Завершает сессию."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE game_sessions SET status = 'completed', finished_at = NOW()
                WHERE id = $1
            ''', session_id)