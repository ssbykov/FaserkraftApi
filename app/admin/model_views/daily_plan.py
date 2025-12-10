from app.admin.custom_model_view import CustomModelView
from app.admin.filters.daily_plan import EmployeeFilter
from app.database import DailyPlan
from app.database.crud.daily_plans import DailyPlanRepository


class DailyPlanAdmin(
    CustomModelView[DailyPlan],
    model=DailyPlan,
):
    repo_type = DailyPlanRepository
    name_plural = "Планы на день"
    name = "План на день"
    category_icon = "fa-solid fa-diagram-project"
    category = "Планирование"

    list_template = "sqladmin/dailyplan_calendar.html"

    column_list = (
        "date",
        "employee",
    )

    column_details_list = (
        "date",
        "employee",
        "steps",
    )

    column_labels = {
        "date": "Дата",
        "employee": "Сотрудник",
        "steps": "Этапы",
    }

    form_columns = [
        "date",
        "employee",
        "steps",
    ]

    form_rules = [
        "date",
        "employee",
        "steps",
    ]

    can_export = False
    can_create = True

    column_filters = [EmployeeFilter()]
