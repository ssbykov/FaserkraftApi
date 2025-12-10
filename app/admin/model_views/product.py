from typing import Any

from sqlalchemy.orm import selectinload

from app.admin.custom_model_view import CustomModelView
from app.admin.filters.process import ProcessNameFilter
from app.admin.utils import format_datetime
from app.database import Product, ProductStep, StepDefinition
from app.database.crud.products import ProductRepository


class ProductAdmin(
    CustomModelView[Product],
    model=Product,
):
    repo_type = ProductRepository
    name_plural = "Изделия"
    name = "Изделие"
    category = "Раздел изделий"
    category_icon = "fa-solid fa-battery-three-quarters"

    column_list = ("serial_number", "process", "created_at")

    column_details_list = (
        "id",
        "serial_number",
        "work_process",
        "created_at",
        "steps",
    )

    column_filters = [ProcessNameFilter()]

    column_labels = {
        "serial_number": "Номер",
        "work_process": "Техпроцесс",
        "created_at": "Запуск в производство",
        "steps": "Этапы",
    }

    form_rules = [
        "serial_number",
        "created_at",
    ]

    can_edit = True
    can_delete = True
    can_export = False

    column_formatters_detail = {
        "created_at": format_datetime,
    }

    column_formatters = {
        "created_at": format_datetime,
    }
