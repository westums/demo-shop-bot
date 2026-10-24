import re
from datetime import datetime, timedelta

SEP = "────────────"

MSK = timedelta(hours=3)
MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

STATUS_LABELS = {
    "new": "🆕 Новый",
    "paid": "💰 Оплачен",
    "shipped": "📦 Отправлен",
    "delivered": "✅ Доставлен",
    "cancelled": "❌ Отменён",
}

STATUS_MESSAGES = {
    "new": "Заказ принят и ожидает оплаты.",
    "paid": "Оплата получена! Собираем ваш заказ. 🎉",
    "shipped": "Курьер уже в пути! Ожидайте в течение 1–2 дней. 🚚",
    "delivered": "Заказ доставлен. Спасибо за покупку! ❤️",
    "cancelled": "К сожалению, заказ отменён. Если это ошибка — свяжитесь с нами.",
}

FREE_DELIVERY_FROM = 3000
DELIVERY_COST = 300


def fmt_price(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " ₽"


def fmt_date(iso_str: str, with_time: bool = False) -> str:
    """2026-10-24 12:56:00 → '24 октября 2026' или '24 октября 2026, 15:56' (MSK)."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.strptime(iso_str[:19], "%Y-%m-%d %H:%M:%S") + MSK
    except (ValueError, TypeError):
        return str(iso_str)[:10]
    if with_time:
        return f"{dt.day} {MONTHS_RU[dt.month - 1]} {dt.year}, {dt:%H:%M}"
    return f"{dt.day} {MONTHS_RU[dt.month - 1]} {dt.year}"


def calc_delivery(items_total: int) -> int:
    if items_total == 0 or items_total >= FREE_DELIVERY_FROM:
        return 0
    return DELIVERY_COST


def mask_name(name: str) -> str:
    if not name:
        return "***"
    parts = [p for p in name.split() if p]
    return " ".join(p[0] + "." for p in parts) or "***"


def mask_phone(phone: str) -> str:
    if not phone:
        return "***"
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "***"
    return f"+{digits[0]} *** *** {digits[-2:]}"


def mask_address(address: str) -> str:
    if not address:
        return "***"
    return address[0] + "***"


def product_card(product: dict) -> str:
    sizes = [s.strip() for s in (product.get("sizes") or "").split(",") if s.strip()]
    lines = [
        f"🛍 <b>{product['name']}</b>",
        SEP,
        "",
        product.get("description") or "",
        "",
    ]
    if product.get("material"):
        lines.append(f"🧵 <b>Материал:</b> {product['material']}")
    if product.get("color"):
        lines.append(f"🎨 <b>Цвет:</b> {product['color']}")
    if product.get("country"):
        lines.append(f"🌍 <b>Производство:</b> {product['country']}")
    if sizes:
        lines.append(f"📏 <b>Размеры:</b> {' · '.join(sizes)}")
    lines.append("📦 <b>Наличие:</b> ✅ в наличии")
    lines.append("")
    lines.append(f"💰 <b>{fmt_price(product['price'])}</b>")
    lines.append(
        f"🚚 Доставка {fmt_price(DELIVERY_COST)} · "
        f"бесплатно от {fmt_price(FREE_DELIVERY_FROM)}"
    )
    lines.append(SEP)
    lines.append("📏 Выберите размер:" if sizes else "👇 Добавьте товар в корзину")
    return "\n".join(lines)


def cart_summary(items: list[dict]) -> tuple[str, int]:
    """Возвращает (текст корзины, итоговая сумма с доставкой)."""
    lines = ["🛒 <b>ВАША КОРЗИНА</b>", SEP, ""]
    items_total = 0
    for item in items:
        subtotal = item["price"] * item["quantity"]
        items_total += subtotal
        size = f" · размер {item['size']}" if item["size"] else ""
        lines.append(f"<b>{item['name']}</b>")
        lines.append(f"   {item['quantity']} шт{size} · {fmt_price(subtotal)}")
        lines.append("")
    delivery = calc_delivery(items_total)
    grand_total = items_total + delivery
    lines.append(SEP)
    lines.append(f"💰 Товары: {fmt_price(items_total)}")
    if delivery == 0:
        lines.append("🚚 Доставка: <b>бесплатно</b>")
    else:
        lines.append(f"🚚 Доставка: {fmt_price(delivery)}")
    lines.append(f"📦 <b>К оплате: {fmt_price(grand_total)}</b>")
    lines.append(SEP)
    return "\n".join(lines), grand_total


def order_notification(order: dict, new_status: str) -> str:
    label = STATUS_LABELS.get(new_status, new_status)
    message = STATUS_MESSAGES.get(new_status, "")
    items_text = "\n".join(
        f"   • {i['product_name']}"
        + (f" ({i['size']})" if i.get("size") else "")
        + f" × {i['quantity']}"
        for i in order["items"]
    )
    return (
        f"📦 <b>Статус заказа обновлён</b>\n"
        f"{SEP}\n\n"
        f"🧾 Заказ <b>#{order['id']}</b>\n"
        f"📅 {fmt_date(order['created_at'], with_time=True)}\n\n"
        f"Новый статус: <b>{label}</b>\n"
        f"<i>{message}</i>\n\n"
        f"<b>Состав:</b>\n{items_text}\n\n"
        f"💰 Итого: <b>{fmt_price(order['total'])}</b>\n\n"
        f"{SEP}\n"
        f"💡 Все заказы → «📦 Мои заказы»"
    )