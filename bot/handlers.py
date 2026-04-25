from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from game.world import make_new_world
from storage.session_service import SessionService
from storage.redis_client import get_redis

router = Router()

# Клавиатура главного меню
def main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔄 Новая игра")
    builder.button(text="💡 Подсказка")
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    redis = message.bot.redis  # мы добавим redis в bot в main.py
    service = SessionService(redis)

    game_path = make_new_world()
    if game_path is None:
        await message.answer("Не удалось создать игру. Попробуйте позже.")
        return

    session = await service.create_session(message.from_user.id, game_path)
    await message.answer(
        session.state["feedback"],
        reply_markup=main_keyboard()
    )

@router.message(F.text.lower() == "🔄 новая игра")
async def new_game(message: types.Message):
    # Просто перенаправляем на старт
    await cmd_start(message)

@router.message(F.text.lower() == "💡 подсказка")
async def hint_request(message: types.Message):
    await message.answer("⏳ Генерация подсказки... (скоро заработает!)")

@router.message(F.text)
async def handle_move(message: types.Message):
    redis = message.bot.redis
    service = SessionService(redis)
    session = await service.get_session(message.from_user.id)

    if not session:
        await message.answer("Игра не найдена. Нажмите '🔄 Новая игра' или отправьте /start.",
                             reply_markup=main_keyboard())
        return

    feedback, commands, done = session.step(message.text)

    if done:
        response = f"{feedback}\n\nИгра окончена! Начните новую, нажав кнопку."
        await service.delete_session(message.from_user.id)
    else:
        # Формируем ответ со списком доступных команд (как у вас было)
        cmd_list = " ; ".join(commands) if commands else "Нет доступных команд"
        response = f"{feedback}\n\nДопустимые команды:\n{cmd_list}"

    await message.answer(response, reply_markup=main_keyboard())