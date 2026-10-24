import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from database import db
from keyboards import inline
from services.format import (
    SEP, STATUS_LABELS, fmt_price, fmt_date,
    mask_name, mask_phone, mask_address, order_notification,
)

router = Router()
logger = logging.getLogger(__name__)


def _can_edit(order: dict, viewer_id: int) -> bool:
    """Можно менять только свои заказы или демо-заказы."""
    return order.get("is_demo") == 1 or order["user_id"] == viewer_id


async def _render_admin_list(viewer_id: int):
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
        "📋 Выберите заказ.\n"
        "💡 Свои и демо-заказы можно редактировать.\n"
        "🔒 Чужие реальные заказы — только для просмотра (данные скрыты)."
    )
    return text, inline.admin_orders_kb(orders)


@router.message(F.text == "🔧 Админ-панель (демо)")
async def admin_panel(message: Message):
    text, kb = await _render_admin_list(message.from_user.id)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    text, kb = await _render_admin_list(callback.from_user.id)
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

    can_edit = _can_edit(order, callback.from_user.id)
    is_own = order["user_id"] == callback.from_user.id
    is_demo = order.get("is_demo") == 1

    # Данные клиента
    if can_edit:
        client_block = (
            f"👤 Клиент: {order['full_name']}\n"
            f"🆔 <code>{order['user_id']}</code>\n"
            f"📞 {order['phone']}\n"
            f"📍 {order['address']}\n"
        )
    else:
        client_block = (
            f"👤 Клиент: {mask_name(order['full_name'])}\n"
            f"🆔 <code>скрыт</code>\n"
            f"📞 {mask_phone(order['phone'])}\n"
            f"📍 {mask_address(order['address'])}\n"
            f"🔒 <i>Это чужой заказ — данные скрыты</i>\n"
        )

    items_text = "\n".join(
        f"├ {i['product_name']}"
        + (f" ({i['size']})" if i.get("size") else "")
        + f" × {i['quantity']} = {fmt_price(i['price'] * i['quantity'])}"
        for i in order["items"]
    )
    status_label = STATUS_LABELS.get(order["status"], order["status"])

    badge = ""
    if is_demo:
        badge = "🎭 <i>демо-заказ</i>\n"
    elif is_own:
        badge = "🫵 <i>ваш заказ</i>\n"

    text = (
        f"🧾 <b>Заказ #{order['id']}</b>\n"
        f"{badge}"
        f"{SEP}\n\n"
        f"📅 {fmt_date(order['created_at'], with_time=True)}\n"
        f"{client_block}\n"
        f"<b>Состав:</b>\n{items_text}\n\n"
        f"💰 Итого: <b>{fmt_price(order['total'])}</b>\n"
        f"📌 Статус: <b>{status_label}</b>"
    )

    if can_edit:
        text += f"\n\n{SEP}\nВыберите новый статус:"
        kb = inline.admin_order_actions_kb(order_id)
    else:
        text += f"\n\n{SEP}\n🔒 Редактирование недоступно"
        kb = inline.admin_back_only_kb()

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("setstatus_"))
async def set_status(callback: CallbackQuery):
    _, order_id_str, new_status = callback.data.split("_")
    order_id = int(order_id_str)
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    if not _can_edit(order, callback.from_user.id):
        await callback.answer("🔒 Нельзя менять чужой заказ", show_alert=True)
        return

    await db.update_order_status(order_id, new_status)
    label = STATUS_LABELS.get(new_status, new_status)

    notified = "✅ Клиент уведомлён"
    if order.get("is_demo") == 1:
        notified = "🎭 Демо-заказ — уведомление не отправляется"
    else:
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