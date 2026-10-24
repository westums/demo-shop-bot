from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from database import db
from keyboards import inline
from services.format import SEP, STATUS_LABELS, fmt_price
from services.qr import generate_demo_qr
from states.fsm import OrderFSM

router = Router()


@router.message(OrderFSM.address)
async def process_address(message: Message, state: FSMContext):
    address = message.text.strip()
    data = await state.get_data()
    items = data.get("cart_items", [])
    total = sum(i["price"] * i["quantity"] for i in items)
    user = await db.get_user(message.from_user.id)

    order_id = await db.create_order(
        user_id=message.from_user.id,
        full_name=user["full_name"], phone=user["phone"],
        address=address, total=total, items=items,
    )
    await db.clear_cart(message.from_user.id)
    await state.clear()

    qr_file = generate_demo_qr(order_id)
    await message.answer_photo(
        photo=qr_file,
        caption=(
            f"🧾 <b>ЗАКАЗ #{order_id} СОЗДАН</b>\n"
            f"{SEP}\n\n"
            f"💰 К оплате: <b>{fmt_price(total)}</b>\n"
            f"📍 Адрес: {address}\n\n"
            f"{SEP}\n"
            "🔧 <i>Это демонстрационный QR-код. Здесь могла бы быть ссылка "
            "на оплату через ЮKassa, Telegram Stars или другой сервис.</i>\n\n"
            "После «оплаты» нажмите кнопку ниже 👇"
        ),
        reply_markup=inline.payment_kb(order_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("paid_"))
async def mark_paid(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] != "new":
        await callback.answer("Заказ уже обработан", show_alert=True)
        return

    await db.update_order_status(order_id, "paid")
    try:
        await callback.message.edit_caption(
            caption=(
                f"✅ <b>ЗАКАЗ #{order_id} ОПЛАЧЕН</b>\n"
                f"{SEP}\n\n"
                "Спасибо за покупку! 🎉\n"
                "Мы уже собираем ваш заказ.\n\n"
                f"{SEP}\n"
                "🔔 Уведомим вас, когда статус изменится.\n"
                "Следить за заказами → «📦 Мои заказы»"
            ),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer("Оплата подтверждена (демо)")


@router.message(F.text == "📦 Мои заказы")
async def my_orders(message: Message):
    orders = await db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer(
            "📦 <b>МОИ ЗАКАЗЫ</b>\n"
            f"{SEP}\n\n"
            "У вас пока нет заказов.\n"
            "Загляните в каталог — там много интересного!",
            parse_mode="HTML",
        )
        return

    lines = ["📦 <b>МОИ ЗАКАЗЫ</b>", SEP, ""]
    for o in orders:
        label = STATUS_LABELS.get(o["status"], o["status"])
        lines.append(f"<b>#{o['id']}</b> · {o['created_at'][:10]} · {fmt_price(o['total'])}")
        lines.append(f"   {label}")
        lines.append("")
    lines.append(SEP)
    lines.append("💡 Уведомления о смене статуса приходят автоматически.")
    await message.answer("\n".join(lines), parse_mode="HTML")