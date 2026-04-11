from database import SessionDep
from database.crud.mixines import GetBackNextIdMixin
from database.models import Order


def get_order_repo(session: SessionDep) -> "OrderRepository":
    return OrderRepository(session)


class OrderRepository(GetBackNextIdMixin[Order]):
    model = Order
