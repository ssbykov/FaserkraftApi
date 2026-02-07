from datetime import date as date_type

from fastapi import HTTPException
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
        employee_id: int,
        date: date_type,
    ) -> DailyPlan:
        stmt = (
            select(self.model)
            .options(
                joinedload(self.model.employee),
                joinedload(self.model.steps)
                .joinedload(DailyPlanStep.step_definition)
                .joinedload(StepDefinition.template),
            )
            .where(
                self.model.employee_id == employee_id,
                self.model.date == date,
            )
        )

        daily_plan = await self.session.scalar(stmt)

        if daily_plan is not None:
            return daily_plan

        raise HTTPException(
            status_code=404,
            detail=f"План для employee_id={employee_id} " f"и даты {date} не найден",
        )
