import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from database import db
from keyboards import inline
from services.format import SEP, product_card
from states.fsm import AddToCart

router = Router()
logger = logging.getLogger(__name__)

PAGE_SIZE = 5


async def _edit(callback: CallbackQuery, text: str, kb):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.warning("edit error: %s", e)


async def _send_text(callback: CallbackQuery, text: str, kb):
    if callback.message.photo:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                logger.warning("edit error: %s", e)


def _page_suffix(page: int, total: int, page_size: int) -> str:
    """Возвращает ' · стр. 2/3' если страниц больше одной, иначе пусто."""
    total_pages = (total + page_size - 1) // page_size
    if total_pages <= 1:
        return ""
    return f" · стр. {page + 1}/{total_pages}"


@router.message(F.text == "🛍 Каталог")
async def show_categories(message: Message):
    categories = await db.get_categories()
    text = "🛍 <b>КАТАЛОГ</b>\n" + SEP + "\n\nВыберите категорию:"
    await message.answer(text, reply_markup=inline.categories_kb(categories), parse_mode="HTML")


@router.callback_query(F.data == "back_categories")
async def back_to_categories(callback: CallbackQuery):
    categories = await db.get_categories()
    text = "🛍 <b>КАТАЛОГ</b>\n" + SEP + "\n\nВыберите категорию:"
    await _send_text(callback, text, inline.categories_kb(categories))
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def show_products(callback: CallbackQuery):
    _, cat_id_str, page_str = callback.data.split("_")
    cat_id, page = int(cat_id_str), int(page_str)

    cats = await db.get_categories()
    cat_name = next((c["name"] for c in cats if c["id"] == cat_id), "")

    total = await db.count_products_in_category(cat_id)
    products = await db.get_products_by_category(cat_id, offset=page * PAGE_SIZE, limit=PAGE_SIZE)

    if not products:
        await callback.answer("В этой категории пока нет товаров", show_alert=True)
        return

    text = (
        f"🛍 <b>КАТАЛОГ</b> → {cat_name}"
        f"{_page_suffix(page, total, PAGE_SIZE)}\n"
        f"{SEP}\n\n"
        "Выберите товар:"
    )
    await _send_text(callback, text,
                     inline.products_kb(products, cat_id, page, total, PAGE_SIZE, cat_name))
    await callback.answer()


@router.callback_query(F.data.startswith("prod_"))
async def show_product(callback: CallbackQuery):
    parts = callback.data.split("_")
    product_id = int(parts[1])
    cat_id = int(parts[2]) if len(parts) > 2 else 0
    page = int(parts[3]) if len(parts) > 3 else 0

    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    sizes = [s.strip() for s in (product.get("sizes") or "").split(",") if s.strip()]
    caption = product_card(product)
    kb = inline.product_kb(product_id, cat_id, page, sizes)

    if callback.message.photo:
        await _edit(callback, caption, kb)
    elif product.get("photo_url"):
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        try:
            await callback.message.answer_photo(
                photo=product["photo_url"], caption=caption,
                reply_markup=kb, parse_mode="HTML",
            )
            await callback.answer()
            return
        except Exception as e:
            logger.warning("Не удалось отправить фото %s: %s", product_id, e)
        await callback.message.answer(caption, reply_markup=kb, parse_mode="HTML")
    else:
        await _edit(callback, caption, kb)
    await callback.answer()


# ---------- Выбор размера / количества ----------

@router.callback_query(F.data.startswith("size_"))
async def pick_size(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    product_id, size = int(parts[1]), parts[2]
    cat_id, page = int(parts[3]), int(parts[4])

    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    await state.set_state(AddToCart.choosing_qty)
    await state.update_data(product_id=product_id, size=size, qty=1, cat_id=cat_id, page=page)

    text = (
        f"🛍 <b>{product['name']}</b>\n"
        f"{SEP}\n\n"
        f"📏 Размер: <b>{size}</b>\n"
        f"💰 Цена: {product['price']} ₽\n\n"
        f"{SEP}\n"
        "Выберите количество:"
    )
    await _edit(callback, text, inline.qty_kb(1))
    await callback.answer()


@router.callback_query(F.data.startswith("add_"))
async def pick_qty_no_size(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    product_id = int(parts[1])
    cat_id = int(parts[2]) if len(parts) > 2 else 0
    page = int(parts[3]) if len(parts) > 3 else 0

    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    sizes = [s.strip() for s in (product.get("sizes") or "").split(",") if s.strip()]
    if sizes:
        await callback.answer("Сначала выберите размер", show_alert=True)
        return

    await state.set_state(AddToCart.choosing_qty)
    await state.update_data(product_id=product_id, size="", qty=1, cat_id=cat_id, page=page)

    text = (
        f"🛍 <b>{product['name']}</b>\n"
        f"{SEP}\n\n"
        f"💰 Цена: {product['price']} ₽\n\n"
        f"{SEP}\n"
        "Выберите количество:"
    )
    await _edit(callback, text, inline.qty_kb(1))
    await callback.answer()


async def _render_qty(callback: CallbackQuery, state: FSMContext, delta: int):
    data = await state.get_data()
    if not data.get("product_id"):
        await callback.answer("Сессия истекла, начните заново", show_alert=True)
        return

    new_qty = max(1, data["qty"] + delta)
    if new_qty > 99:
        await callback.answer("Не больше 99 шт", show_alert=True)
        return
    data["qty"] = new_qty
    await state.update_data(qty=new_qty)

    product = await db.get_product(data["product_id"])
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    size_line = f"📏 Размер: <b>{data['size']}</b>\n" if data["size"] else ""
    text = (
        f"🛍 <b>{product['name']}</b>\n"
        f"{SEP}\n\n"
        f"{size_line}"
        f"💰 Цена: {product['price']} ₽\n\n"
        f"{SEP}\n"
        "Выберите количество:"
    )
    await _edit(callback, text, inline.qty_kb(new_qty))
    await callback.answer()


@router.callback_query(AddToCart.choosing_qty, F.data == "qty_inc")
async def qty_inc(callback: CallbackQuery, state: FSMContext):
    await _render_qty(callback, state, +1)


@router.callback_query(AddToCart.choosing_qty, F.data == "qty_dec")
async def qty_dec(callback: CallbackQuery, state: FSMContext):
    await _render_qty(callback, state, -1)


@router.callback_query(AddToCart.choosing_qty, F.data == "qty_add")
async def qty_add(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("product_id"):
        await callback.answer("Сессия истекла", show_alert=True)
        return

    await db.add_to_cart(callback.from_user.id, data["product_id"], data["size"], data["qty"])
    product = await db.get_product(data["product_id"])
    size_part = f" (размер {data['size']})" if data["size"] else ""
    added = f"✅ <b>{product['name']}</b>{size_part} × {data['qty']} шт добавлено в корзину"

    cat_id, page = data.get("cat_id", 0), data.get("page", 0)
    await state.clear()

    cats = await db.get_categories()
    cat_name = next((c["name"] for c in cats if c["id"] == cat_id), "")
    total = await db.count_products_in_category(cat_id)
    products = await db.get_products_by_category(cat_id, offset=page * PAGE_SIZE, limit=PAGE_SIZE)

    if products:
        text = (
            f"{added}\n\n"
            f"{SEP}\n"
            f"🛍 <b>КАТАЛОГ</b> → {cat_name}"
            f"{_page_suffix(page, total, PAGE_SIZE)}\n\n"
            "Выберите товар:"
        )
        await _send_text(callback, text,
                         inline.products_kb(products, cat_id, page, total, PAGE_SIZE, cat_name))
    else:
        await _send_text(callback, added, None)
    await callback.answer("Добавлено ✅")


@router.callback_query(AddToCart.choosing_qty, F.data == "qty_cancel")
async def qty_cancel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    product_id = data.get("product_id")
    if product_id:
        product = await db.get_product(product_id)
        if product:
            sizes = [s.strip() for s in (product.get("sizes") or "").split(",") if s.strip()]
            caption = product_card(product)
            kb = inline.product_kb(product_id, data.get("cat_id", 0), data.get("page", 0), sizes)
            await _edit(callback, caption, kb)
            await callback.answer("Отменено")
            return

    categories = await db.get_categories()
    await _send_text(callback, "🛍 <b>КАТАЛОГ</b>\n" + SEP + "\n\nВыберите категорию:",
                     inline.categories_kb(categories))
    await callback.answer("Отменено")


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()