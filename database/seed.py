import aiosqlite
from database.db import DB_PATH


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


async def seed_data():
    async with aiosqlite.connect(DB_PATH) as db:
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