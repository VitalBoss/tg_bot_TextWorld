from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from game.world import make_new_world, GameSession
from storage.session_service import SessionService
import os

router = Router()

def main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔄 Новая игра")
    builder.button(text="💡 Подсказка")
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    redis = message.bot.redis
    service = SessionService(redis)
    logger = message.bot.logger

    game_path = make_new_world()
    if game_path is None:
        await message.answer("Не удалось создать игру. Попробуйте позже.")
        return

    await service.create_session(message.from_user.id, game_path)
    # Создаём сессию в PostgreSQL
    session_id = await logger.start_session(message.from_user.id, game_path)
    # Сохраняем pg_session_id в Redis для связи
    await redis.set(f"pg_session:{message.from_user.id}", session_id)

    session = GameSession(game_path)
    feedback = session.state["feedback"]
    await message.answer(feedback, reply_markup=main_keyboard())

@router.message(F.text.lower() == "🔄 новая игра")
async def new_game(message: types.Message):
    await cmd_start(message)

@router.message(F.text.lower() == "💡 подсказка")
async def hint_request(message: types.Message):
    redis = message.bot.redis
    service = SessionService(redis)
    game_path, history = await service.get_session(message.from_user.id)

    if game_path is None:
        await message.answer("Игра не найдена. Начните новую игру.", reply_markup=main_keyboard())
        return

    # Восстанавливаем сессию
    session = GameSession(game_path)
    for cmd in history:
        session.step(cmd)

    feedback = session.state.get("feedback", "")
    commands = session.state.get("admissible_commands", [])

    thinking_msg = await message.answer("⏳ Генерирую подсказку...")

    try:
        from llm.hint_generator import generate_hint
        hint = await generate_hint(feedback, commands)
        await thinking_msg.edit_text(f"💡 Подсказка:\n\n{hint}")
    except Exception as e:
        await thinking_msg.edit_text("❌ Не удалось получить подсказку. Попробуйте позже.")
        print(f"Ошибка GigaChat: {e}")

@router.message(F.text)
async def handle_move(message: types.Message):
    redis = message.bot.redis
    service = SessionService(redis)
    logger = message.bot.logger
    game_path, history = await service.get_session(message.from_user.id)

    if game_path is None:
        await message.answer("Игра не найдена. Нажмите '🔄 Новая игра' или отправьте /start.",
                             reply_markup=main_keyboard())
        return

    session = GameSession(game_path)
    for cmd in history:
        session.step(cmd)

    feedback, commands, done = session.step(message.text)

    # Получаем pg_session_id
    pg_session_id = await redis.get(f"pg_session:{message.from_user.id}")
    if pg_session_id:
        pg_session_id = pg_session_id.decode("utf-8") if isinstance(pg_session_id, bytes) else pg_session_id
        move_number = len(history) + 1
        await logger.log_move(pg_session_id, move_number, message.text, feedback, commands)

    if done:
        response = f"{feedback}\n\nИгра окончена! Начните новую, нажав кнопку."
        if pg_session_id:
            await logger.finish_session(pg_session_id)
        await service.delete_session(message.from_user.id)
        await redis.delete(f"pg_session:{message.from_user.id}")
    else:
        history.append(message.text)
        await service.save_history(message.from_user.id, history)
        cmd_list = " ; ".join(commands) if commands else "Нет доступных команд"
        response = f"{feedback}\n\nДопустимые команды:\n{cmd_list}"

    await message.answer(response, reply_markup=main_keyboard())

@router.message(Command("register"))
async def cmd_register(message: types.Message):
    # Проверяем, есть ли аргумент (токен)
    try:
        token = message.text.split()[1]
    except IndexError:
        await message.answer("Использование: /register <токен>")
        return

    if token != os.getenv("REGISTER_TOKEN"):
        await message.answer("Неверный токен.")
        return

    # Регистрируем пользователя
    pool = message.bot.db_pool
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (telegram_id, username) VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE SET username = $2
        ''', message.from_user.id, message.from_user.username or "player")
    await message.answer("Вы успешно зарегистрированы!")