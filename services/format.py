SEP = "━━━━━━━━━━━━━━━━━━"

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


def fmt_price(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " ₽"


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
    lines.append(f"🚚 Доставка 1–3 дня · бесплатно от {fmt_price(FREE_DELIVERY_FROM)}")
    lines.append(SEP)
    lines.append("📏 Выберите размер:" if sizes else "👇 Добавьте товар в корзину")
    return "\n".join(lines)


def cart_summary(items: list[dict]) -> tuple[str, int]:
    lines = ["🛒 <b>ВАША КОРЗИНА</b>", SEP, ""]
    total = 0
    for item in items:
        subtotal = item["price"] * item["quantity"]
        total += subtotal
        size = f" · размер {item['size']}" if item["size"] else ""
        lines.append(f"<b>{item['name']}</b>")
        lines.append(f"   {item['quantity']} шт{size} · {fmt_price(subtotal)}")
        lines.append("")
    lines.append(SEP)
    lines.append(f"💰 Товары: {fmt_price(total)}")
    if total >= FREE_DELIVERY_FROM:
        lines.append("🚚 Доставка: <b>бесплатно</b>")
    else:
        lines.append(f"🚚 Доставка: от {fmt_price(FREE_DELIVERY_FROM)} — бесплатно")
    lines.append(f"📦 <b>К оплате: {fmt_price(total)}</b>")
    lines.append(SEP)
    return "\n".join(lines), total


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
        f"📅 {order['created_at'][:16]}\n\n"
        f"Новый статус: <b>{label}</b>\n"
        f"<i>{message}</i>\n\n"
        f"<b>Состав:</b>\n{items_text}\n\n"
        f"💰 Итого: <b>{fmt_price(order['total'])}</b>\n\n"
        f"{SEP}\n"
        f"💡 Все заказы → «📦 Мои заказы»"
    )