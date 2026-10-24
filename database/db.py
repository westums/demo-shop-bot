import aiosqlite
import os
from pathlib import Path
from typing import Optional

_data_dir = os.getenv("DATA_DIR", "")
if _data_dir:
    DB_PATH = str(Path(_data_dir) / "shop.db")
else:
    DB_PATH = str(Path(__file__).resolve().parent.parent / "shop.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone TEXT,
                consent_given INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                photo_url TEXT,
                sizes TEXT DEFAULT '',
                material TEXT DEFAULT '',
                color TEXT DEFAULT '',
                country TEXT DEFAULT '',
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                size TEXT DEFAULT '',
                quantity INTEGER DEFAULT 1,
                UNIQUE(user_id, product_id, size)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                total INTEGER NOT NULL,
                status TEXT DEFAULT 'new',
                is_demo INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                size TEXT DEFAULT '',
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
        await db.commit()


# ---------- Пользователи ----------

async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, full_name: str, phone: str = None, consent: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, full_name, phone, consent_given) VALUES (?, ?, ?, ?)",
            (user_id, full_name, phone, 1 if consent else 0),
        )
        await db.commit()


async def update_user_phone(user_id: int, phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        await db.commit()


async def delete_user_data(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM orders WHERE user_id = ?", (user_id,)) as cur:
            order_ids = [r[0] for r in await cur.fetchall()]
        for oid in order_ids:
            await db.execute("DELETE FROM order_items WHERE order_id = ?", (oid,))
        await db.execute("DELETE FROM orders WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()


# ---------- Категории и товары ----------

async def get_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM categories") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def count_products_in_category(category_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,)
        ) as cur:
            return (await cur.fetchone())[0]


async def get_products_by_category(category_id: int, offset: int = 0, limit: int = 100):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE category_id = ? LIMIT ? OFFSET ?",
            (category_id, limit, offset),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_product(product_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# ---------- Корзина ----------

async def add_to_cart(user_id: int, product_id: int, size: str = '', qty: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO cart (user_id, product_id, size, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, product_id, size)
            DO UPDATE SET quantity = quantity + excluded.quantity
        """, (user_id, product_id, size, qty))
        await db.commit()


async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.id, c.product_id, c.size, c.quantity,
                   p.name, p.price, p.photo_url
            FROM cart c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ?
        """, (user_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def update_cart_quantity(user_id: int, product_id: int, size: str, delta: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT quantity FROM cart WHERE user_id = ? AND product_id = ? AND size = ?",
            (user_id, product_id, size),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        new_qty = row[0] + delta
        if new_qty <= 0:
            await db.execute(
                "DELETE FROM cart WHERE user_id = ? AND product_id = ? AND size = ?",
                (user_id, product_id, size),
            )
            await db.commit()
            return False
        await db.execute(
            "UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ? AND size = ?",
            (new_qty, user_id, product_id, size),
        )
        await db.commit()
        return True


async def remove_from_cart(user_id: int, product_id: int, size: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM cart WHERE user_id = ? AND product_id = ? AND size = ?",
            (user_id, product_id, size),
        )
        await db.commit()


async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()


# ---------- Заказы ----------

async def create_order(user_id: int, full_name: str, phone: str, address: str,
                       total: int, items: list[dict], is_demo: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders (user_id, full_name, phone, address, total, is_demo) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, full_name, phone, address, total, is_demo),
        )
        order_id = cur.lastrowid
        for item in items:
            await db.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, size, price, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, item["product_id"], item["name"], item.get("size", ""),
                  item["price"], item["quantity"]))
        await db.commit()
        return order_id


async def get_user_orders(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE user_id = ? AND is_demo = 0 ORDER BY id DESC",
            (user_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_all_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders ORDER BY id DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            order = await cur.fetchone()
        if not order:
            return None
        order = dict(order)
        async with db.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
        ) as cur:
            order["items"] = [dict(r) for r in await cur.fetchall()]
        return order


async def update_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM orders"
        ) as cur:
            total_orders, total_sum = await cur.fetchone()
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'new'"
        ) as cur:
            new_orders = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]
        return {
            "total_orders": total_orders,
            "total_sum": total_sum,
            "new_orders": new_orders,
            "total_users": total_users,
        }