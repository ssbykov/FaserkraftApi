from datetime import date as date_type

from sqlalchemy import select, exists
from sqlalchemy.orm import joinedload

from app.database import DailyPlan, SessionDep, StepDefinition, ProductStep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import DailyPlanStep


def get_daily_plan_repo(session: SessionDep) -> "DailyPlanRepository":
    return DailyPlanRepository(session)


class DailyPlanRepository(GetBackNextIdMixin[DailyPlan]):
    model = DailyPlan

    async def get(
        self,
        *,
        date: date_type,
        employee_id: int | None = None,
    ) -> list[DailyPlan]:
        stmt = (
            select(self.model)
            .options(
                joinedload(self.model.employee),
                joinedload(self.model.steps)
                .joinedload(DailyPlanStep.step_definition)
                .joinedload(StepDefinition.template),
            )
            .where(self.model.date == date)
        )

        if employee_id is not None:
            stmt = stmt.where(self.model.employee_id == employee_id)

        result = await self.session.execute(stmt)
        return result.unique().scalars().all()

    async def check_step_in_daily_plan(
        self,
        *,
        date: date_type,
        employee_id: int,
        product_step_id: int,
    ):
        # 1. subquery на step_definition_id нужного ProductStep
        step_def_id_stmt = select(ProductStep.step_definition_id).where(
            ProductStep.id == product_step_id
        )
        step_def_id_subq = step_def_id_stmt.scalar_subquery()

        # 2. EXISTS по DailyPlan + DailyPlanStep с таким же step_definition_id
        subq = (
            select(DailyPlanStep.id)
            .join(DailyPlan, DailyPlanStep.daily_plan_id == DailyPlan.id)
            .where(
                DailyPlan.employee_id == employee_id,
                DailyPlan.date == date,
                DailyPlanStep.step_definition_id == step_def_id_subq,
            )
        )

        stmt = select(exists(step_def_id_subq))
        result = await self.session.execute(stmt)
        return bool(result.scalar())
