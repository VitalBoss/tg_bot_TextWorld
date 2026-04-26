import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from bot.handlers import router
from storage.redis_client import get_redis
from storage.postgres import get_pool, init_db
from storage.session_logger import SessionLogger
import time

load_dotenv()

async def main():
    bot = Bot(
        token=os.getenv("BOT_TOKEN"),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    bot.redis = await get_redis()

    # Подключаемся к PostgreSQL (теперь он точно доступен)
    pool = await get_pool()
    await init_db(pool)
    bot.db_pool = pool
    bot.logger = SessionLogger(pool)

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await dp.start_polling(bot)