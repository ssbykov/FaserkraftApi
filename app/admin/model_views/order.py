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

    column_list = ("contract_number", "contract_date", "planned_shipment_date")
    column_details_exclude_list = ("id", "shipment_by_id")

    column_labels = {
        "contract_number": "Номер договора",
        "contract_date": "Дата договора",
        "planned_shipment_date": "Дата факт",
        "shipment_by": "Отправлено",
        "shipment_date": "Дата план",
        "items": "Состав заказ",
        "packaging": "Упаковки",
    }

    can_export = False
