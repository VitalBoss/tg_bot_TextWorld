import sys
print("=== START ===", flush=True)
sys.stdout.flush()
# DATABASE_URL=postgresql://bot:secret@db:5432/textworld_bot
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

load_dotenv()

async def main():
    print("===== Бот запускается... =====")
    
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
        return
    print(f"✅ Токен загружен (первые 10 символов): {token[:10]}...")
    
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    
    print("⏳ Подключаюсь к Redis...")
    try:
        bot.redis = await get_redis()
        print("✅ Redis подключён")
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        return

    print("⏳ Подключаюсь к PostgreSQL...")
    try:
        pool = await get_pool()
        await init_db(pool)
        bot.db_pool = pool
        bot.logger = SessionLogger(pool)
        print("✅ PostgreSQL подключён, таблицы инициализированы")
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        import traceback
        traceback.print_exc()
        return

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    print("⏳ Запускаю поллинг...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка при поллинге: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())