from typing import Any

from sqlalchemy.orm import selectinload

from app.admin.custom_model_view import CustomModelView
from app.database import Process, StepDefinition
from app.database.crud.processes import ProcessRepository


class ProcessAdmin(
    CustomModelView[Process],
    model=Process,
):
    repo_type = ProcessRepository
    name_plural = "Процессы"
    name = "Процесс"
    icon = "fa-solid fa-diagram-project"
    category = "Раздел процессов"
    category_icon = "fa-solid fa-cog"

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "steps": "Этапы",
    }

    column_list = ("name", "description")

    column_details_list = (
        "name",
        "description",
        "steps",
    )

    form_rules = [
        "name",
        "description",
        "steps",
    ]

    can_edit = True
    can_delete = True
    can_export = False

    def format_steps(self, _):
        return [
            f"{getattr(s, 'order', None)}: "
            f"{getattr(getattr(s, 'template', None), 'name', '-')}"
            for s in getattr(self, "steps", []) or []
        ]

    column_formatters_detail = {
        "steps": format_steps,
    }

    async def get_object_for_details(self, value: Any) -> Any:
        pk = value.get("path_params", {}).get("pk")
        stmt = self._stmt_by_identifier(pk)

        stmt = stmt.options(
            selectinload(Process.steps).selectinload(StepDefinition.template)
        )
        return await self._get_object_by_pk(stmt)
