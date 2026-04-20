from app.admin.custom_model_view import CustomModelView
from app.database.crud.packaging_box import PackagingRepository
from app.database.models import Packaging


class PackagingAdmin(
    CustomModelView[Packaging],
    model=Packaging,
):
    repo_type = PackagingRepository
    name_plural = "Упаковки"
    name = "Упаковка"
    category = "Раздел изделий"
    category_icon = "fa-solid fa-cog"

    column_labels = {
        "serial_number": "Номер",
        "description": "Описание",
        "products": "Изделия",
        "performed_by": "Упаковщик",
        "performed_at": "Дата упаковки",
        "order": "Заказ",
    }

    column_list = ("id", "serial_number")

    column_details_exclude_list = ["performed_by_id", "shipment_by_id", "order_id"]

    can_edit = True
    can_delete = True
    can_export = False