import logging
from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger("bot.middleware")

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        user_id = None
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
        elif hasattr(event, 'message') and event.message:
            user_id = event.message.from_user.id
        # Логируем входящее событие
        logger.info(f"Update from user_id={user_id}, type={event.event_type}")
        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception(f"Unhandled exception for user_id={user_id}: {e}")
            # Опционально можно отправить сообщение администратору
            raise