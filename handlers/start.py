import re

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards import reply, inline
from services.format import SEP, fmt_price, fmt_date
from states.fsm import Registration

router = Router()

WELCOME_TEXT = (
    "🛍 <b>DEMOSHOP</b>\n"
    "<i>магазин одежды · демо-версия</i>\n"
    f"{SEP}\n\n"
    "👋 Привет! Это демонстрационный Telegram-бот магазина, созданный как портфолио-проект.\n\n"
    "✨ <b>Что здесь можно сделать:</b>\n"
    "├ 🛍 Полистать каталог\n"
    "├ 🛒 Собрать корзину\n"
    "├ 💳 Оформить заказ (оплата демо)\n"
    "├ 📦 Следить за статусом\n"
    "└ 🔧 Побывать в роли админа\n\n"
    "💡 <i>Фишка: зайдите в админку, смените статус заказа — и получите уведомление как клиент!</i>\n\n"
    f"{SEP}\n"
    "Для продолжения примите согласие на обработку ПД 👇"
)

ABOUT_TEXT = (
    "ℹ️ <b>О боте</b>\n"
    f"{SEP}\n\n"
    "🛍 <b>DemoShop</b> — демонстрационный Telegram-бот магазина одежды.\n\n"
    "👨‍💻 <b>Технологии:</b>\n"
    "├ Python 3.13\n"
    "├ aiogram 3.x\n"
    "├ SQLite (aiosqlite)\n"
    "├ qrcode + Pillow\n"
    "└ python-dotenv\n\n"
    "✨ <b>Возможности:</b>\n"
    "├ регистрация с согласием на обработку ПД\n"
    "├ каталог с размерами и фото\n"
    "├ корзина с количеством\n"
    "├ демо-оплата через QR\n"
    "├ уведомления о смене статуса\n"
    "├ демо-админка\n"
    "└ удаление своих данных одной кнопкой\n\n"
    "🔗 <b>Исходный код:</b> <a href='https://github.com/westums/shop-bot'>GitHub</a>\n"
    f"{SEP}\n"
    "💡 <i>Все заказы и платежи — демонстрационные, реальных операций нет.</i>"
)


def _valid_name(text: str) -> bool:
    text = text.strip()
    if len(text) < 2 or len(text) > 50:
        return False
    # Только буквы (кириллица/латиница), пробелы и дефисы
    return bool(re.fullmatch(r"[A-Za-zА-Яа-яЁё\s\-]+", text))


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return raw.strip()
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return f"+7 {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    if len(digits) == 10:
        return f"+7 {digits[0:3]} {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    if raw.strip().startswith("+"):
        return raw.strip()
    return "+" + digits


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if user:
        await message.answer(
            f"С возвращением, <b>{user['full_name']}</b>! 👋\n\nВыберите раздел в меню 👇",
            reply_markup=reply.main_menu(),
            parse_mode="HTML",
        )
        return

    with open("consent.txt", "r", encoding="utf-8") as f:
        consent_text = f.read()

    await message.answer(WELCOME_TEXT, parse_mode="HTML")
    await message.answer(
        consent_text + "\n\n👇 Нажмите «✅ Согласен», чтобы продолжить регистрацию.",
        reply_markup=reply.consent_kb(),
    )
    await state.set_state(Registration.consent)


@router.message(Registration.consent, F.text == "✅ Согласен")
async def consent_accepted(message: Message, state: FSMContext):
    await state.update_data(consent=True)
    await message.answer(
        "Как вас зовут? (Имя и фамилия — например, <i>Иван Петров</i>)",
        reply_markup=reply.cancel_kb(), parse_mode="HTML",
    )
    await state.set_state(Registration.full_name)


@router.message(Registration.full_name, F.text == "❌ Отмена")
async def reg_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Регистрация отменена. Напишите /start, чтобы начать заново.",
        reply_markup=reply.main_menu(),
    )


@router.message(Registration.full_name)
async def reg_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not _valid_name(name):
        await message.answer(
            "❌ Пожалуйста, введите имя буквами (от 2 до 50 символов).\n"
            "Например: <i>Иван Петров</i>",
            reply_markup=reply.cancel_kb(), parse_mode="HTML",
        )
        return
    await state.update_data(full_name=name)
    await message.answer(
        "Приятно познакомиться! Теперь отправьте номер телефона кнопкой ниже "
        "или напишите вручную (например, +7 999 123-45-67).",
        reply_markup=reply.phone_kb(),
    )
    await state.set_state(Registration.phone)


@router.message(Registration.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext):
    phone = _normalize_phone(message.contact.phone_number)
    await finish_registration(message, state, phone)


@router.message(Registration.phone, F.text)
async def reg_phone_text(message: Message, state: FSMContext):
    phone = _normalize_phone(message.text.strip())
    await finish_registration(message, state, phone)


async def finish_registration(message: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    await db.create_user(message.from_user.id, data["full_name"], phone, True)
    await state.clear()
    await message.answer(
        "🎉 <b>Регистрация завершена!</b>\n\n"
        "Добро пожаловать в DemoShop. Выберите раздел в меню 👇",
        reply_markup=reply.main_menu(), parse_mode="HTML",
    )


# ---------- Профиль ----------

@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return

    orders = await db.get_user_orders(message.from_user.id)
    total_spent = sum(o["total"] for o in orders)

    text = (
        "👤 <b>ПРОФИЛЬ</b>\n"
        f"{SEP}\n\n"
        f"👋 <b>{user['full_name']}</b>\n"
        f"📞 {user['phone'] or '—'}\n"
        f"🆔 <code>{user['user_id']}</code>\n"
        f"📅 С нами с {fmt_date(user['created_at'])}\n\n"
        f"📦 Заказов: <b>{len(orders)}</b>\n"
        f"💰 Потрачено: <b>{fmt_price(total_spent)}</b>\n\n"
        f"🔐 Согласие на обработку ПД: {'✅ да' if user['consent_given'] else '❌ нет'}\n"
        f"{SEP}\n"
        "💡 Удалить свои данные можно кнопкой ниже."
    )
    await message.answer(text, reply_markup=reply.profile_kb(), parse_mode="HTML")


@router.message(F.text == "⬅️ В меню")
async def back_to_menu(message: Message):
    await message.answer("Главное меню 👇", reply_markup=reply.main_menu())


@router.message(F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    await message.answer(ABOUT_TEXT, parse_mode="HTML", disable_web_page_preview=True)


# ---------- Удаление данных ----------

@router.message(F.text == "🗑 Удалить мои данные")
async def delete_my_data_prompt(message: Message):
    await message.answer(
        "⚠️ <b>Вы уверены?</b>\n\n"
        "Будут удалены:\n"
        "├ ваш профиль\n"
        "├ корзина\n"
        "└ все ваши заказы\n\n"
        "Действие необратимо.",
        reply_markup=inline.confirm_delete_kb(), parse_mode="HTML",
    )


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text("Отменено. Ваши данные в безопасности 👍")
    await callback.answer()


@router.callback_query(F.data == "confirm_delete")
async def confirm_delete(callback: CallbackQuery):
    await db.delete_user_data(callback.from_user.id)
    await callback.message.edit_text(
        "🗑 <b>Все ваши данные удалены.</b>\n\n"
        "Спасибо, что пользовались DemoShop!\n"
        "Если захотите вернуться — напишите /start.",
        parse_mode="HTML",
    )
    await callback.answer("Данные удалены")


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message):
    await delete_my_data_prompt(message)