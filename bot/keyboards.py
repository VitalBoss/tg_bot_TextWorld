from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def main_menu(has_incomplete: bool = False):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🕹 Новая игра")
    builder.button(text="📊 Статистика")
    builder.button(text="📜 Справка")
    return builder.as_markup(resize_keyboard=True)

def main_menu_inline():
    builder = InlineKeyboardBuilder()
    builder.button(text="🕹 Новая игра", callback_data="newgame")
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.button(text="📜 Справка", callback_data="help")
    return builder.as_markup()

def game_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🕹 Новая игра")
    builder.button(text="💡 Подсказка")
    builder.button(text="🏁 Завершить игру")
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