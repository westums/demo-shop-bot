from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from database import db
from keyboards import inline
from services.format import SEP, cart_summary
from states.fsm import OrderFSM

router = Router()


async def _render_cart(user_id: int) -> tuple[str, any]:
    items = await db.get_cart(user_id)
    if not items:
        return (
            "🛒 <b>КОРЗИНА ПУСТА</b>\n"
            f"{SEP}\n\n"
            "Загляните в каталог — там много интересного 👇",
            None,
        )
    text, _ = cart_summary(items)
    return text, inline.cart_items_kb(items)


@router.message(F.text == "🛒 Корзина")
async def show_cart(message: Message):
    text, kb = await _render_cart(message.from_user.id)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("cart_plus_") | F.data.startswith("cart_minus_"))
async def change_qty(callback: CallbackQuery):
    parts = callback.data.split("_")
    action, product_id = parts[1], int(parts[2])
    size = parts[3] if len(parts) > 3 else ""
    delta = 1 if action == "plus" else -1

    await db.update_cart_quantity(callback.from_user.id, product_id, size, delta)
    text, kb = await _render_cart(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("cart_del_"))
async def delete_item(callback: CallbackQuery):
    parts = callback.data.split("_")
    product_id = int(parts[2])
    size = parts[3] if len(parts) > 3 else ""

    await db.remove_from_cart(callback.from_user.id, product_id, size)
    text, kb = await _render_cart(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer("Удалено")


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    await db.clear_cart(callback.from_user.id)
    try:
        await callback.message.edit_text(
            "🗑 <b>Корзина очищена</b>\n\nЗагляните в каталог за новыми покупками!",
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    items = await db.get_cart(callback.from_user.id)
    if not items:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    await state.update_data(cart_items=items)
    await state.set_state(OrderFSM.address)
    await callback.message.answer(
        "📍 <b>Оформление заказа</b>\n"
        f"{SEP}\n\n"
        "Введите адрес доставки:\n"
        "<i>город, улица, дом, квартира</i>",
        parse_mode="HTML",
    )
    await callback.answer()