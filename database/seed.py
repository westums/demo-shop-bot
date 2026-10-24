import aiosqlite
from database.db import DB_PATH
from services.format import calc_delivery


PRODUCTS = [
    (1, "Базовая белая футболка",
     "Идеальная база под любую одежду. Свободный крой, унисекс.",
     1500,
     "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800",
     "S,M,L,XL", "100% хлопок", "белый", "Турция"),
    (1, "Футболка с принтом",
     "Оверсайз, чёрная. Плотный хлопок, принт не выцветает после стирок.",
     1900,
     "https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=800",
     "S,M,L,XL", "100% хлопок", "чёрный", "Турция"),
    (2, "Джинсы прямые",
     "Классический крой, синий деним. Подходят под всё.",
     4500,
     "https://images.unsplash.com/photo-1542272604-787c3835535d?w=800",
     "28,30,32,34,36", "98% хлопок, 2% эластан", "синий", "Турция"),
    (2, "Джинсы скинни",
     "Эластичные, чёрные. Отлично сидят, не растягиваются.",
     4200,
     "https://images.unsplash.com/photo-1475178626620-a4d074967452?w=800",
     "28,30,32,34,36", "92% хлопок, 6% полиэстер, 2% эластан", "чёрный", "Турция"),
    (3, "Куртка-бомбер",
     "Хаки, водоотталкивающая. Демисезонный вариант.",
     6800,
     "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800",
     "S,M,L,XL", "полиэстер", "хаки", "Китай"),
    (4, "Кроссовки белые",
     "Кожаные, минималистичный дизайн. Универсальная пара на каждый день.",
     5500,
     "https://images.unsplash.com/photo-1600269452121-4f2416e55c28?w=800",
     "36,37,38,39,40,41,42,43,44,45", "натуральная кожа", "белый", "Вьетнам"),
]


# Демо-заказы: (status, address, [(product_id, name, size, price, qty)])
DEMO_USER_ID = 100000000
DEMO_USER_NAME = "Александра Смирнова"
DEMO_USER_PHONE = "+7 900 123-45-67"

DEMO_ORDERS = [
    ("delivered", "Москва, ул. Тверская, 12, кв. 45", [
        (6, "Кроссовки белые", "42", 5500, 1),
    ]),
    ("shipped", "Санкт-Петербург, Невский пр., 88, кв. 12", [
        (1, "Базовая белая футболка", "M", 1500, 2),
        (3, "Джинсы прямые", "32", 4500, 1),
    ]),
    ("paid", "Казань, ул. Баумана, 5, кв. 3", [
        (2, "Футболка с принтом", "L", 1900, 1),
    ]),
]


async def seed_data():
    async with aiosqlite.connect(DB_PATH) as db:
        # Категории и товары
        async with db.execute("SELECT COUNT(*) FROM categories") as cur:
            count = (await cur.fetchone())[0]
        if count == 0:
            categories = [
                ("👕 Футболки",),
                ("👖 Джинсы",),
                ("🧥 Куртки",),
                ("👟 Обувь",),
            ]
            await db.executemany("INSERT INTO categories (name) VALUES (?)", categories)
            await db.executemany(
                "INSERT INTO products "
                "(category_id, name, description, price, photo_url, sizes, material, color, country) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                PRODUCTS,
            )
            await db.commit()

        # Демо-заказы (только если их ещё нет)
        async with db.execute("SELECT COUNT(*) FROM orders WHERE is_demo = 1") as cur:
            demo_count = (await cur.fetchone())[0]
        if demo_count == 0:
            for status, address, items in DEMO_ORDERS:
                items_total = sum(price * qty for _, _, _, price, qty in items)
                delivery = calc_delivery(items_total)
                grand_total = items_total + delivery

                cur = await db.execute(
                    "INSERT INTO orders "
                    "(user_id, full_name, phone, address, total, status, is_demo) "
                    "VALUES (?, ?, ?, ?, ?, ?, 1)",
                    (DEMO_USER_ID, DEMO_USER_NAME, DEMO_USER_PHONE,
                     address, grand_total, status),
                )
                order_id = cur.lastrowid
                for pid, pname, size, price, qty in items:
                    await db.execute(
                        "INSERT INTO order_items "
                        "(order_id, product_id, product_name, size, price, quantity) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (order_id, pid, pname, size, price, qty),
                    )
            await db.commit()