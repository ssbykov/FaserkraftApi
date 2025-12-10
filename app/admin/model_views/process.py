from sqladmin import action
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.custom_model_view import CustomModelView
from app.database import Process, db_helper
from app.database.crud.processes import ProcessRepository


class ProcessAdmin(
    CustomModelView[Process],
    model=Process,
):
    repo_type = ProcessRepository
    name_plural = "Процессы"
    name = "Процесс"
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
