from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import DailyPlan, SessionDep, StepDefinition
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
