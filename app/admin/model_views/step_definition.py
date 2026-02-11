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
    category = "Раздел процессов"

    column_labels = {
        StepDefinition.work_process: "Процесс",
        StepDefinition.template: "Шаблон",
        StepDefinition.order: "Порядок",
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

    form_args = {
        "work_process": {
            "label": "Процесс",
        }
    }

    form_columns = [
        StepDefinition.template,
        StepDefinition.order,
        StepDefinition.work_process,
    ]

    can_edit = True
    can_delete = True
    can_export = False
