from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.admin.custom_model_view import CustomModelView
from app.database import DailyPlan, StepDefinition
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
        "daily_plan",
        "step_definition",
        "planned_quantity",
        "actual_quantity",
    )

    column_details_list = (
        "daily_plan",
        "step_definition",
        "planned_quantity",
        "actual_quantity",
    )

    column_labels = {
        "daily_plan": "План для:",
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

    def format_daily_plan(self, _) -> str:
        if isinstance(self, DailyPlanStep):
            return f"{self.daily_plan.employee.name} на {self.daily_plan.date}"
        return ""

    def format_step_definition(self, _) -> str:
        if isinstance(self, DailyPlanStep):
            return (
                f"{self.step_definition.template} - {self.step_definition.work_process}"
            )
        return ""

    column_formatters_detail = {
        "daily_plan": format_daily_plan,
        "step_definition": format_step_definition,
    }

    column_formatters = {
        "daily_plan": format_daily_plan,
        "step_definition": format_step_definition,
    }

    # async def get_object_for_edit(self, request: Request) -> Any:
    #     stmt = self.form_edit_query(request)
    #     stmt = stmt.options(
    #         selectinload(DailyPlanStep.daily_plan).selectinload(DailyPlan.employee),
    #         # цепочка до template
    #         selectinload(DailyPlanStep.step_definition).selectinload(
    #             StepDefinition.template
    #         ),
    #         # и отдельная опция для product_steps от StepDefinition
    #         selectinload(DailyPlanStep.step_definition).selectinload(
    #             StepDefinition.product_steps
    #         ),
    #     )
    #
    #     return await self._get_object_by_pk(stmt)

    def is_visible(self, request: Request) -> bool:
        return False

    def list_query(self, request: Request = None):
        from sqlalchemy.orm import selectinload

        stmt = super().list_query(request)
        stmt = stmt.options(
            selectinload(DailyPlanStep.daily_plan).selectinload(DailyPlan.employee),
            selectinload(DailyPlanStep.step_definition),
            selectinload(DailyPlanStep.step_definition).selectinload(
                StepDefinition.template
            ),
            selectinload(DailyPlanStep.step_definition).selectinload(
                StepDefinition.work_process
            ),
        )
        return stmt

    async def get_object_for_details(self, request):
        pk = request.path_params.get("pk") or request.query_params.get("pks")
        stmt = self._stmt_by_identifier(pk)
        stmt = stmt.options(
            selectinload(DailyPlanStep.daily_plan).selectinload(DailyPlan.employee),
            # цепочка до template
            selectinload(DailyPlanStep.step_definition).selectinload(
                StepDefinition.template
            ),
            selectinload(DailyPlanStep.step_definition).selectinload(
                StepDefinition.work_process
            ),
        )

        return await self._get_object_by_pk(stmt)

    can_export = False
    can_create = True
