from typing import Any

from sqladmin import action
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.custom_model_view import CustomModelView
from app.database import Process, StepDefinition, db_helper
from app.database.crud.processes import ProcessRepository


class ProcessAdmin(
    CustomModelView[Process],
    model=Process,
):
    repo_type = ProcessRepository
    name_plural = "Процессы"
    name = "Процесс"
    # icon = "fa-solid fa-diagram-project"
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

    action_in_header = ["copy-process"]

    @action(
        name="copy-process",
        label="Скопировать процесс",
        add_in_detail=True,
        add_in_list=False,
        confirmation_message=f"Создать копию процесса?",
    )
    async def generate_qr(self, request: Request) -> RedirectResponse:
        if pks := request.query_params["pks"]:
            async for session in db_helper.get_session():
                repo = self.repo_type(session)
                await repo.copy_process(process_id=int(pks))

        return RedirectResponse(request.url_for("admin:list", identity=self.identity))
