from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat["name"], callback_data=f"cat_{cat['id']}_0")
    builder.adjust(2)
    return builder.as_markup()


def products_kb(products: list[dict], cat_id: int, page: int,
                total: int, page_size: int, category_name: str = "") -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        rows.append([InlineKeyboardButton(
            text=f"{p['name']} — {p['price']} ₽",
            callback_data=f"prod_{p['id']}_{cat_id}_{page}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"cat_{cat_id}_{page - 1}"))
    if (page + 1) * page_size < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"cat_{cat_id}_{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 К категориям", callback_data="back_categories")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_kb(product_id: int, cat_id: int, page: int, sizes: list[str]) -> InlineKeyboardMarkup:
    rows = []
    if sizes:
        row = []
        for s in sizes:
            row.append(InlineKeyboardButton(
                text=s,
                callback_data=f"size_{product_id}_{s}_{cat_id}_{page}",
            ))
            if len(row) == 4:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
    else:
        rows.append([InlineKeyboardButton(
            text="🛒 Добавить в корзину",
            callback_data=f"add_{product_id}_{cat_id}_{page}",
        )])
    rows.append([InlineKeyboardButton(
        text="⬅️ К товарам",
        callback_data=f"cat_{cat_id}_{page}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def qty_kb(qty: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖", callback_data="qty_dec"),
            InlineKeyboardButton(text=f" {qty} ", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data="qty_inc"),
        ],
        [InlineKeyboardButton(text="✅ Добавить в корзину", callback_data="qty_add")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="qty_cancel")],
    ])


def cart_items_kb(items: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        pid = item["product_id"]
        size = item["size"] or ""
        rows.append([
            InlineKeyboardButton(text="−", callback_data=f"cart_minus_{pid}_{size}"),
            InlineKeyboardButton(text=f"{item['quantity']} шт", callback_data="noop"),
            InlineKeyboardButton(text="+", callback_data=f"cart_plus_{pid}_{size}"),
            InlineKeyboardButton(text="🗑", callback_data=f"cart_del_{pid}_{size}"),
        ])
    rows.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")])
    rows.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{order_id}")],
    ])


def admin_orders_kb(orders: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for o in orders:
        builder.button(
            text=f"Заказ #{o['id']} — {o['total']} ₽ — {o['status']}",
            callback_data=f"admin_order_{o['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def admin_order_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    statuses = [
        ("🆕 Новый", "new"),
        ("💰 Оплачен", "paid"),
        ("📦 Отправлен", "shipped"),
        ("✅ Доставлен", "delivered"),
        ("❌ Отменён", "cancelled"),
    ]
    builder = InlineKeyboardBuilder()
    for label, status in statuses:
        builder.button(text=label, callback_data=f"setstatus_{order_id}_{status}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ К списку заказов", callback_data="admin_back"))
    return builder.as_markup()


def confirm_delete_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Да, удалить всё", callback_data="confirm_delete")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")],
    ])