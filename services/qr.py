import qrcode
from io import BytesIO
from aiogram.types import BufferedInputFile

def generate_demo_qr(order_id: int) -> BufferedInputFile:
    """Генерирует QR-код с демо-строкой. Реальной оплаты не происходит."""
    data = f"DEMO_PAYMENT_ORDER_{order_id}_NOT_REAL"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return BufferedInputFile(buf.read(), filename=f"qr_order_{order_id}.png")