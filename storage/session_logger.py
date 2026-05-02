class SessionLogger:
    def __init__(self, pool):
        self.pool = pool

    async def start_session(self, user_id: int, game_path: str, quest_name: str, difficulty: str) -> str:
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (telegram_id, username) VALUES ($1, 'player')
                ON CONFLICT (telegram_id) DO NOTHING
            ''', user_id)
            user_db_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', user_id)
            session_id = await conn.fetchval('''
                INSERT INTO game_sessions (user_id, game_file_path, quest_name, difficulty, status)
                VALUES ($1, $2, $3, $4, 'active')
                RETURNING id
            ''', user_db_id, game_path, quest_name, difficulty)
            return str(session_id)

    async def log_move(self, session_id: str, move_number: int, command: str, feedback: str, admissible_commands: list):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO game_moves (session_id, move_number, command, feedback, admissible_commands)
                VALUES ($1, $2, $3, $4, $5)
            ''', session_id, move_number, command, feedback, admissible_commands)

    async def update_session_status(self, session_id: str, status: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE game_sessions SET status = $1 WHERE id = $2",
                status, session_id
            )
            if status in ('completed', 'abandoned'):
                await conn.execute(
                    "UPDATE game_sessions SET finished_at = NOW() WHERE id = $1",
                    session_id
                )

    async def save_quest(self, user_id: int, session_id: str, difficulty: str, success: bool, steps_count: int, reward: int):
        async with self.pool.acquire() as conn:
            quest_name = await conn.fetchval('SELECT quest_name FROM game_sessions WHERE id = $1', session_id)
            if not quest_name:
                quest_name = 'Unknown Quest'
            user_db_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', user_id)
            await conn.execute('''
                INSERT INTO completed_quests (user_id, session_id, quest_name, difficulty, success, steps_count, reward)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', user_db_id, session_id, quest_name, difficulty, success, steps_count, reward)

    async def get_completed_quests(self, user_id: int) -> list:
        async with self.pool.acquire() as conn:
            user_db_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', user_id)
            if not user_db_id:
                return []
            rows = await conn.fetch('''
                SELECT quest_name, difficulty, success, steps_count, reward, completed_at
                FROM completed_quests
                WHERE user_id = $1
                ORDER BY completed_at DESC
            ''', user_db_id)
            return [dict(row) for row in rows]

    async def get_stats_by_difficulty(self, user_id: int) -> dict:
        async with self.pool.acquire() as conn:
            user_db_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', user_id)
            if not user_db_id:
                return {}
            rows = await conn.fetch('''
                SELECT difficulty,
                       COUNT(*) as total,
                       COUNT(CASE WHEN success THEN 1 END) as successful,
                       COUNT(CASE WHEN NOT success THEN 1 END) as failed,
                       AVG(CASE WHEN success THEN steps_count END) as avg_steps_success,
                       AVG(CASE WHEN NOT success THEN steps_count END) as avg_steps_fail
                FROM completed_quests
                WHERE user_id = $1
                GROUP BY difficulty
            ''', user_db_id)
            return {row['difficulty']: dict(row) for row in rows}

    async def get_last_incomplete_session(self, user_id: int) -> dict | None:
        async with self.pool.acquire() as conn:
            user_db_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', user_id)
            if not user_db_id:
                return None
            row = await conn.fetchrow('''
                SELECT id, game_file_path, quest_name, difficulty, status
                FROM game_sessions
                WHERE user_id = $1 AND status IN ('active','paused')
                ORDER BY started_at DESC LIMIT 1
            ''', user_db_id)
            return dict(row) if row else None