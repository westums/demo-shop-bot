from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Каталог")],
            [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="📦 Мои заказы")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="ℹ️ О боте")],
            [KeyboardButton(text="🔧 Админ-панель (демо)")],
        ],
        resize_keyboard=True,
    )


def consent_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Согласен")]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить телефон", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def profile_kb(bot_username: str = "") -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🗑 Удалить мои данные")],
        [KeyboardButton(text="⬅️ В меню")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)