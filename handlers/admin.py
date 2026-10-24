import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database import db
from keyboards import inline
from services.format import SEP, STATUS_LABELS, fmt_price, order_notification

router = Router()
logger = logging.getLogger(__name__)


async def _render_admin_list():
    stats = await db.get_stats()
    orders = await db.get_all_orders()
    if not orders:
        return (
            "🔧 <b>АДМИН-ПАНЕЛЬ</b>\n"
            f"{SEP}\n\n"
            "📊 <b>Статистика:</b>\n"
            f"├ 👥 Пользователей: {stats['total_users']}\n"
            "├ 🛒 Заказов: 0\n"
            "└ 💰 Оборот: 0 ₽\n\n"
            f"{SEP}\n"
            "Пока нет заказов. Оформите первый из каталога!",
            None,
        )

    text = (
        "🔧 <b>АДМИН-ПАНЕЛЬ</b>\n"
        "<i>демо-режим · доступна всем</i>\n"
        f"{SEP}\n\n"
        "📊 <b>Статистика:</b>\n"
        f"├ 👥 Пользователей: {stats['total_users']}\n"
        f"├ 🛒 Заказов: {stats['total_orders']}\n"
        f"├ 💰 Оборот: {fmt_price(stats['total_sum'])}\n"
        f"└ 🆕 Новых: {stats['new_orders']}\n\n"
        f"{SEP}\n"
        "📋 Выберите заказ, чтобы сменить статус.\n"
        "💡 Клиент получит уведомление об изменении."
    )
    return text, inline.admin_orders_kb(orders)


@router.message(F.text == "🔧 Админ-панель (демо)")
async def admin_panel(message: Message):
    text, kb = await _render_admin_list()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    text, kb = await _render_admin_list()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("admin_order_"))
async def admin_order_detail(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    items_text = "\n".join(
        f"├ {i['product_name']}"
        + (f" ({i['size']})" if i.get("size") else "")
        + f" × {i['quantity']} = {fmt_price(i['price'] * i['quantity'])}"
        for i in order["items"]
    )
    status_label = STATUS_LABELS.get(order["status"], order["status"])

    text = (
        f"🧾 <b>Заказ #{order['id']}</b>\n"
        f"{SEP}\n\n"
        f"📅 {order['created_at'][:16]}\n"
        f"👤 Клиент: {order['full_name']}\n"
        f"🆔 <code>{order['user_id']}</code>\n"
        f"📞 {order['phone']}\n"
        f"📍 {order['address']}\n\n"
        f"<b>Состав:</b>\n{items_text}\n\n"
        f"💰 Итого: <b>{fmt_price(order['total'])}</b>\n"
        f"📌 Статус: <b>{status_label}</b>\n\n"
        f"{SEP}\n"
        "Выберите новый статус:"
    )
    try:
        await callback.message.edit_text(
            text, reply_markup=inline.admin_order_actions_kb(order_id), parse_mode="HTML",
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text, reply_markup=inline.admin_order_actions_kb(order_id), parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("setstatus_"))
async def set_status(callback: CallbackQuery):
    _, order_id_str, new_status = callback.data.split("_")
    order_id = int(order_id_str)
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    await db.update_order_status(order_id, new_status)
    label = STATUS_LABELS.get(new_status, new_status)

    notified = "✅ Клиент уведомлён"
    try:
        await callback.bot.send_message(
            order["user_id"], order_notification(order, new_status), parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Не удалось уведомить клиента %s: %s", order["user_id"], e)
        notified = "⚠️ Не удалось уведомить (бот заблокирован?)"

    try:
        await callback.message.edit_text(
            f"✅ <b>Статус обновлён</b>\n"
            f"{SEP}\n\n"
            f"Заказ <b>#{order_id}</b>\n"
            f"Новый статус: {label}\n\n"
            f"{notified}",
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer("Статус изменён")