import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from bot.handlers import router
from storage.redis_client import get_redis
from storage.postgres import get_pool, init_db
from storage.session_logger import SessionLogger

load_dotenv()

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://your-domain.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

APP_HOST = "0.0.0.0"
APP_PORT = int(os.getenv("APP_PORT", 3001))

async def on_startup(bot: Bot):
    # Инициализация БД и кэша
    bot.redis = await get_redis()
    pool = await get_pool()
    await init_db(pool)
    bot.db_pool = pool
    bot.logger = SessionLogger(pool)

    # Устанавливаем вебхук
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    await bot.session.close()
    # Закрываем соединения с БД и Redis
    if hasattr(bot, 'db_pool'):
        await bot.db_pool.close()
    if hasattr(bot, 'redis'):
        await bot.redis.close()

async def healthcheck(request):
    """Проверяем, что бот и инфраструктура живы."""
    bot = request.app['bot']
    try:
        # Проверка Redis
        await bot.redis.ping()
        # Проверка PostgreSQL
        async with bot.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "detail": str(e)}, status=500)

async def webhook_handler(request):
    """Передаём входящие запросы от Telegram в aiogram."""
    bot = request.app['bot']
    dp = request.app['dispatcher']
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_webhook_update(bot, update)
    return web.Response()

def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    app = web.Application()
    app['bot'] = bot
    app['dispatcher'] = dp

    # Эндпоинты
    app.router.add_post(WEBHOOK_PATH, webhook_handler)
    app.router.add_get("/health", healthcheck)
    app.router.add_get("/", lambda r: web.Response(text="Bot is running"))

    # Обработчики жизненного цикла
    app.on_startup.append(lambda app: on_startup(app['bot']))
    app.on_shutdown.append(lambda app: on_shutdown(app['bot']))

    # Запускаем веб-сервер
    web.run_app(app, host=APP_HOST, port=APP_PORT)

if __name__ == "__main__":
    main()