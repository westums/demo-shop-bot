import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from config import BOT_TOKEN
from database.db import init_db
from database.seed import seed_data
from handlers import start, catalog, cart, order, admin

logger = logging.getLogger(__name__)


def setup_logging():
    log_path = os.path.join(os.getenv("DATA_DIR", "."), "bot.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


async def on_error(event: ErrorEvent):
    logger.exception("Ошибка при обработке update: %s", event.exception)
    update = event.update
    try:
        if update.message:
            await update.message.answer(
                "😔 Что-то пошло не так. Попробуйте ещё раз или напишите /start."
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "Ошибка, попробуйте ещё раз", show_alert=True
            )
    except Exception:
        pass


async def main():
    setup_logging()
    logger.info("Запуск бота...")

    await init_db()
    await seed_data()
    logger.info("БД инициализирована, демо-данные засеяны")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.errors.register(on_error)

    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(order.router)
    dp.include_router(admin.router)

    logger.info("Все роутеры подключены, старт polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")