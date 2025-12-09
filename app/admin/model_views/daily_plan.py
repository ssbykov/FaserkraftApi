from sqlalchemy.orm import selectinload

from app.admin.custom_model_view import CustomModelView
from app.database import DailyPlan, StepDefinition
from app.database.crud.daily_plans import DailyPlanRepository
from app.database.models import DailyPlanStep


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

    def format_steps(self, _):
        return [
            f"{getattr(sd := s.step_definition, 'template', None)}: "
            f"{getattr(getattr(sd, 'process', None), 'name', '-')}"
            for s in getattr(self, "steps", []) or []
        ]

    column_formatters_detail = {
        "steps": format_steps,
    }

    async def get_object_for_details(self, request):
        pk = request.path_params.get("pk") or request.query_params.get("pks")
        stmt = self._stmt_by_identifier(pk)
        stmt = stmt.options(
            selectinload(DailyPlan.steps)
            .selectinload(DailyPlanStep.step_definition)
            .selectinload(StepDefinition.template),
            selectinload(DailyPlan.steps)
            .selectinload(DailyPlanStep.step_definition)
            .selectinload(StepDefinition.process),
        )

        return await self._get_object_by_pk(stmt)
