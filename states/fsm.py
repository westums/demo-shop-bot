from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    consent = State()
    full_name = State()
    phone = State()


class OrderFSM(StatesGroup):
    address = State()


class AddToCart(StatesGroup):
    choosing_qty = State()