from app.admin.custom_model_view import CustomModelView
from app.database import StepTemplate
from app.database.crud.step_templates import StepTemplateRepository


class StepTemplateAdmin(
    CustomModelView[StepTemplate],
    model=StepTemplate,
):
    repo_type = StepTemplateRepository
    name_plural = "Шаблоны этапов"
    name = "Шаблон этапа"
    # icon = "fa-solid fa-bars"
    category = "Раздел процессов"

    column_list = ("name", "description")

    column_details_list = ("name", "description")

    column_labels = {
        "name": "Название",
        "description": "Описание",
    }

    form_create_rules = [
        "name",
        "description",
    ]
    form_edit_rules = form_create_rules.copy()

    can_edit = True
    can_delete = True
    can_export = False
