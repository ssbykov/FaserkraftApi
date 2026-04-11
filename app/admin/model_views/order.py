from app.admin.custom_model_view import CustomModelView
from database.crud.orders import OrderRepository
from database.models import Order


class OrderAdmin(
    CustomModelView[Order],
    model=Order,
):
    repo_type = OrderRepository
    name_plural = "Заказы"
    name = "Заказ"
    category = "Отгрузки"

    column_details_exclude_list = ("id",)
    column_exclude_list = ("id", "items", "packaging")

    column_labels = {
        "contract_number": "Номер договора",
        "contract_date": "Дата договора",
        "planned_shipment_date": "Дата исполнения",
        "items": "Состав заказ",
        "packaging": "Упаковки",
    }

    can_export = False
