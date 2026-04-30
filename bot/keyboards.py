from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🕹 Новая игра")
    builder.button(text="📊 Статистика")
    builder.button(text="📜 Справка")
    return builder.as_markup(resize_keyboard=True)


def game_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔄 Новая игра")
    builder.button(text="💡 Подсказка")
    builder.button(text="⏸ Пауза")
    return builder.as_markup(resize_keyboard=True)

def difficulty_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 Лёгкий", callback_data="difficulty_easy")
    builder.button(text="🟡 Средний", callback_data="difficulty_medium")
    builder.button(text="🔴 Сложный", callback_data="difficulty_hard")
    return builder.as_markup()

def confirm_new_game_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, начать новую", callback_data="newgame_yes")
    builder.button(text="❌ Отмена", callback_data="newgame_no")
    return builder.as_markup()