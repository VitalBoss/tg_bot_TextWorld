from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from game.world import make_new_world, GameSession
from storage.session_service import SessionService
import os
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from bot.keyboards import (
    main_menu, game_menu, difficulty_keyboard, confirm_new_game_keyboard
)

router = Router()

def main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔄 Новая игра")
    builder.button(text="💡 Подсказка")
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать в TextWorld!")
    logger = message.bot.logger
    incomplete = await logger.get_last_incomplete_session(message.from_user.id)
    if incomplete:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Да, продолжить", callback_data="continue_yes")
        builder.button(text="❌ Нет, завершить", callback_data="continue_no")
        await message.answer("У вас есть незавершённая игра. Хотите продолжить?",
                             reply_markup=builder.as_markup())
    else:
        await message.answer("Выберите действие:", reply_markup=main_menu())

@router.message(F.text == "🕹 Новая игра")
async def new_game_prompt(message: types.Message):
    # Проверим, есть ли активная/приостановленная игра
    logger = message.bot.logger
    incomplete = await logger.get_last_incomplete_session(message.from_user.id)
    if incomplete:
        await message.answer("У вас есть незавершённая игра. Хотите завершить её и начать новую?",
                             reply_markup=confirm_new_game_keyboard())
    else:
        await message.answer("Выберите сложность:", reply_markup=difficulty_keyboard())

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

    feedback, commands, done, reward = session.step(message.text)

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

@router.callback_query(F.data == "newgame_yes")
async def abandon_and_new(callback: types.CallbackQuery):
    logger = callback.bot.logger
    redis = callback.bot.redis
    service = SessionService(redis)
    incomplete = await logger.get_last_incomplete_session(callback.from_user.id)
    if incomplete:
        # Помечаем старую как abandoned
        await logger.update_session_status(incomplete['id'], 'abandoned')
        # Удаляем ключи Redis
        await service.delete_session(callback.from_user.id)
        await redis.delete(f"pg_session:{callback.from_user.id}")
    await callback.message.edit_text("Выберите сложность:", reply_markup=difficulty_keyboard())
    await callback.answer()

@router.callback_query(F.data == "newgame_no")
async def cancel_new_game(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("Продолжайте текущую игру.")

@router.callback_query(F.data.startswith("difficulty_"))
async def start_game_with_difficulty(callback: types.CallbackQuery):
    difficulty = callback.data.split("_")[1]  # easy, medium, hard
    redis = callback.bot.redis
    service = SessionService(redis)
    logger = callback.bot.logger

    game_path, quest_name = make_new_world(difficulty)
    if game_path is None:
        await callback.message.answer("Ошибка создания мира. Попробуйте позже.")
        await callback.answer()
        return

    # Сохраняем сессию в Redis и PostgreSQL
    await service.create_session(callback.from_user.id, game_path)
    session_id = await logger.start_session(callback.from_user.id, game_path, quest_name, difficulty)
    await redis.set(f"pg_session:{callback.from_user.id}", session_id)

    session = GameSession(game_path)
    feedback = session.state["feedback"]
    await callback.message.answer(feedback, reply_markup=game_menu())
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

# Пауза
@router.message(F.text == "⏸ Пауза")
async def pause_game(message: types.Message):
    redis = message.bot.redis
    logger = message.bot.logger
    pg_session_id = await redis.get(f"pg_session:{message.from_user.id}")
    if pg_session_id:
        pg_session_id = pg_session_id.decode() if isinstance(pg_session_id, bytes) else pg_session_id
        await logger.update_session_status(pg_session_id, 'paused')
    await message.answer("Игра поставлена на паузу. Возвращайтесь скорее!", reply_markup=main_menu())


# Статистика
@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def show_stats(message: types.Message):
    logger = message.bot.logger
    stats = await logger.get_stats_by_difficulty(message.from_user.id)
    if not stats:
        await message.answer("Статистика пока пуста. Сыграйте хотя бы одну игру!", reply_markup=main_menu())
        return
    text = "📊 Ваша статистика:\n\n"
    for diff, data in stats.items():
        emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(diff, "⚪")
        text += f"{emoji} {diff.capitalize()}:\n"
        text += f"  Игр: {data['total']} | ✅ {data['successful']} | ❌ {data['failed']}\n"
        if data['avg_steps_success']:
            text += f"  Среднее шагов (успех): {data['avg_steps_success']:.1f}\n"
        if data['avg_steps_fail']:
            text += f"  Среднее шагов (провал): {data['avg_steps_fail']:.1f}\n"
        text += "\n"
    # Кнопка списка игр
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Список завершённых игр", callback_data="list_completed")
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "list_completed")
async def list_completed(callback: types.CallbackQuery):
    logger = callback.bot.logger
    quests = await logger.get_completed_quests(callback.from_user.id)
    if not quests:
        await callback.answer("Нет завершённых игр.", show_alert=True)
        return
    text = "📋 Завершённые игры:\n\n"
    for q in quests:
        icon = "✅" if q['success'] else "❌"
        text += f"{icon} {q['quest_name']} ({q['difficulty']}): {q['steps_count']} шагов, награда {q['reward']}\n"
    await callback.message.edit_text(text)
    await callback.answer()

# Обработка хода (обновлённая)
@router.message(F.text)
async def handle_move(message: types.Message):
    redis = message.bot.redis
    service = SessionService(redis)
    logger = message.bot.logger
    game_path, history = await service.get_session(message.from_user.id)

    if game_path is None:
        await message.answer("Игра не найдена. Начните новую игру.", reply_markup=main_menu())
        return

    session = GameSession(game_path)
    for cmd in history:
        session.step(cmd)

    feedback, commands, done, reward = session.step(message.text)

    pg_session_id = await redis.get(f"pg_session:{message.from_user.id}")
    if pg_session_id:
        pg_session_id = pg_session_id.decode() if isinstance(pg_session_id, bytes) else pg_session_id
        move_number = len(history) + 1
        await logger.log_move(pg_session_id, move_number, message.text, feedback, commands)

    if done:
        if pg_session_id:
            diff = await redis.get(f"pg_session_diff:{message.from_user.id}")  # будем сохранять сложность при старте
            if not diff:
                diff = 'medium'  # fallback
            else:
                diff = diff.decode() if isinstance(diff, bytes) else diff
            success = reward > 0
            await logger.save_quest(message.from_user.id, pg_session_id, diff, success, move_number, reward)
            await logger.update_session_status(pg_session_id, 'completed')
        response = f"{feedback}\n\nИгра окончена! Начните новую, нажав кнопку."
        await service.delete_session(message.from_user.id)
        await redis.delete(f"pg_session:{message.from_user.id}", f"pg_session_diff:{message.from_user.id}")
        await message.answer(response, reply_markup=main_menu())
    else:
        history.append(message.text)
        await service.save_history(message.from_user.id, history)
        cmd_list = " ; ".join(commands) if commands else "Нет доступных команд"
        response = f"{feedback}\n\nДопустимые команды:\n{cmd_list}"
        await message.answer(response, reply_markup=game_menu())


@router.callback_query(F.data == "continue_yes")
async def continue_yes(callback: types.CallbackQuery):
    redis = callback.bot.redis
    service = SessionService(redis)
    logger = callback.bot.logger
    incomplete = await logger.get_last_incomplete_session(callback.from_user.id)
    if not incomplete:
        await callback.message.answer("Нет незавершённой игры.")
        await callback.answer()
        return

    # Восстанавливаем статус
    await logger.update_session_status(incomplete['id'], 'active')
    game_path, history = await service.get_session(callback.from_user.id)
    if game_path is None:
        await callback.message.answer("Не удалось восстановить игру. Начните новую.")
        await callback.answer()
        return

    session = GameSession(game_path)
    for cmd in history:
        session.step(cmd)
    feedback = session.state["feedback"]
    await callback.message.answer(feedback, reply_markup=game_menu())
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "continue_no")
async def continue_no(callback: types.CallbackQuery):
    redis = callback.bot.redis
    service = SessionService(redis)
    logger = callback.bot.logger
    incomplete = await logger.get_last_incomplete_session(callback.from_user.id)
    if incomplete:
        await logger.update_session_status(incomplete['id'], 'abandoned')
        await service.delete_session(callback.from_user.id)
        await redis.delete(f"pg_session:{callback.from_user.id}")
    await callback.message.answer("Игра завершена. Выберите действие:", reply_markup=main_menu())
    await callback.message.delete()
    await callback.answer()