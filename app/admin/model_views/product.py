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
        "process",
        "created_at",
        "steps",
    )

    column_filters = [ProcessNameFilter()]

    column_labels = {
        "serial_number": "Номер",
        "process": "Техпроцесс",
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

    def format_steps(self, _):
        return [
            f"{getattr(sd := s.step_definition, 'order', None)}: "
            f"{getattr(getattr(sd, 'template', None), 'name', '-')}"
            f" - {getattr(s.status, 'label', s.status)}"
            for s in getattr(self, "steps", []) or []
        ]

    column_formatters_detail = {
        "steps": format_steps,
        "created_at": format_datetime,
    }

    column_formatters = {
        "created_at": format_datetime,
    }

    async def get_object_for_details(self, value: Any) -> Any:
        pk = value.get("path_params", {}).get("pk") or value.query_params.get("pks")
        stmt = self._stmt_by_identifier(pk)

        stmt = stmt.options(
            selectinload(Product.steps)
            .selectinload(ProductStep.step_definition)
            .selectinload(StepDefinition.template)
        )
        return await self._get_object_by_pk(stmt)
