from app.admin.custom_model_view import CustomModelView
from app.database import StepDefinition
from app.database.crud.step_definitions import StepDefinitionRepository


class StepDefinitionAdmin(
    CustomModelView[StepDefinition],
    model=StepDefinition,
):
    repo_type = StepDefinitionRepository
    name_plural = "Этапы"
    name = "Этап"
    icon = "fa-solid fa-step-forward"
    category = "Раздел процессов"

    column_labels = {
        "work_process": "Процесс",
        "template": "Шаблон",
        "order": "Порядок",
    }

    column_list = (
        "template",
        "work_process",
    )

    column_details_list = (
        "work_process",
        "template",
        "order",
    )

    form_rules = [
        "template",
        "order",
        "work_process",
    ]

    can_edit = True
    can_delete = True
    can_export = False
