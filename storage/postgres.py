import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot:secret@localhost:5432/textworld_bot")

async def get_pool():
    """Создаёт и возвращает пул соединений."""
    return await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

async def init_db(pool):
    """Создаёт таблицы, если их нет."""
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                registered_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS game_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                game_file_path TEXT NOT NULL,
                quest_name TEXT NOT NULL DEFAULT 'Unknown Quest',
                difficulty VARCHAR(10) DEFAULT 'medium',
                status VARCHAR(20) DEFAULT 'active',
                started_at TIMESTAMPTZ DEFAULT NOW(),
                finished_at TIMESTAMPTZ
            );

            CREATE TABLE IF NOT EXISTS game_moves (
                id BIGSERIAL PRIMARY KEY,
                session_id UUID REFERENCES game_sessions(id) ON DELETE CASCADE,
                move_number INTEGER NOT NULL,
                command TEXT NOT NULL,
                feedback TEXT,
                admissible_commands TEXT[],
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS completed_quests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                session_id UUID REFERENCES game_sessions(id) ON DELETE SET NULL,
                quest_name TEXT NOT NULL,
                difficulty VARCHAR(10) NOT NULL,
                success BOOLEAN NOT NULL,
                steps_count INTEGER NOT NULL,
                reward INTEGER NOT NULL,
                completed_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')