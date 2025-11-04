from app.admin.custom_model_view import CustomModelView
from app.database import Process
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

    form_create_rules = [
        "name",
        "description",
        "steps",
    ]
    form_edit_rules = form_create_rules.copy()

    can_edit = True
    can_delete = True
    can_export = False
