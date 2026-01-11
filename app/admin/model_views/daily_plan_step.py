from markupsafe import Markup
from starlette.requests import Request

from app.admin.custom_model_view import CustomModelView
from app.database.crud.daily_plan_steps import DailyPlanStepRepository
from app.database.models import DailyPlanStep


class DailyPlanStepAdmin(
    CustomModelView[DailyPlanStep],
    model=DailyPlanStep,
):
    repo_type = DailyPlanStepRepository
    name_plural = "Планы"
    name = "План на этап"

    column_list = (
        "date",
        "employee_plan",
        "step_definition",
        "work_process",
        "planned_quantity",
        "actual_quantity",
    )

    column_details_list = (
        "daily_plan",
        "work_process",
        "step_definition",
        "planned_quantity",
        "actual_quantity",
    )

    column_formatters_detail = {
        "work_process": lambda m, _: m.work_process,
    }

    column_formatters = {
        "date": lambda m, _: m.date,
        "employee_plan": lambda m, _: Markup(
            f'<a href="/admin/employee/details/{m.daily_plan.employee.id}">'
            f"{m.daily_plan.employee.name}"
            f"</a>"
        ),
    }

    column_labels = {
        "date": "Дата",
        "employee_plan": "Сотрудник",
        "daily_plan": "План для",
        "work_process": "Процесс",
        "step_definition": "Этап",
        "planned_quantity": "Планируемое количество",
        "actual_quantity": "Факт",
    }

    form_columns = [
        "daily_plan",
        "step_definition",
        "planned_quantity",
        "actual_quantity",
    ]

    def is_visible(self, request: Request) -> bool:
        return False

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = False
