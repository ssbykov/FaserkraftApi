from typing import Any

from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.admin.custom_model_view import CustomModelView
from app.database import ProductStep, StepDefinition
from app.database.crud.products_steps import ProductStepRepository


class ProductStepAdmin(
    CustomModelView[ProductStep],
    model=ProductStep,
):
    repo_type = ProductStepRepository
    name_plural = "Этапы изделий"
    name = "Этап изделия"

    column_labels = {
        "product": "Изделие",
        "step_definition": "Название этапа",
        "accepted_by": "Принял",
        "performed_by": "Выполнил",
        "status": "Статус",
        "accepted_at": "Принят",
        "performed_at": "Выполнен",
    }

    column_details_list = (
        "product",
        "step_definition",
        "accepted_by",
        "accepted_at",
        "performed_by",
        "status",
        "performed_at",
    )

    can_edit = True
    can_delete = True
    can_export = False

    def is_visible(self, request: Request) -> bool:
        return False

    def format_steps(self, _) -> str:
        if isinstance(self, ProductStep):
            return self.step_definition.template.name
        return ""

    column_formatters_detail = {
        "step_definition": format_steps,
    }

    async def get_object_for_details(self, value: Any) -> Any:
        pk = value.get("path_params", {}).get("pk") or value.query_params.get("pks")
        stmt = self._stmt_by_identifier(pk)

        stmt = stmt.options(
            selectinload(ProductStep.step_definition).selectinload(
                StepDefinition.template
            )
        )
        return await self._get_object_by_pk(stmt)
