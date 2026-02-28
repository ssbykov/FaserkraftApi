from datetime import date as date_type
from typing import Sequence

from sqlalchemy import select, exists
from sqlalchemy.orm import joinedload, Mapped

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
    ) -> Sequence[DailyPlan]:
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

    async def check_step_def_in_daily_plan(
        self,
        *,
        date: date_type,
        employee_id: Mapped[int],
        step_def_id: Mapped[int],
    ) -> bool:
        subq = (
            select(DailyPlanStep.id)
            .join(DailyPlan, DailyPlanStep.daily_plan_id == DailyPlan.id)
            .where(
                DailyPlan.employee_id == employee_id,
                DailyPlan.date == date,
                DailyPlanStep.step_definition_id == step_def_id,
            )
        )

        stmt = select(exists(subq))
        return bool(await self.session.scalar(stmt))

    async def check_step_in_daily_plan(
        self,
        *,
        date: date_type,
        employee_id: Mapped[int],
        product_step_id: Mapped[int],
    ) -> bool:

        step_def_id = await self.get_step_def(product_step_id=product_step_id)

        if step_def_id is None:
            return False

        return await self.check_step_def_in_daily_plan(
            date=date,
            employee_id=employee_id,
            step_def_id=step_def_id,
        )

    async def get_step_def(
        self,
        *,
        product_step_id: Mapped[int],
    ) -> Mapped[int] | None:

        step_def_id_stmt = select(ProductStep.step_definition_id).where(
            ProductStep.id == product_step_id
        )
        res = await self.session.execute(step_def_id_stmt)
        return res.scalar_one_or_none()

    async def add_step_to_daily_plan(
        self,
        *,
        date: date_type,
        employee_id: Mapped[int],
        step_id: Mapped[int],
        planned_quantity: int = 0,
    ) -> Sequence[DailyPlan]:
        """
        Добавляет этап (через step_id = step_definition_id) в дневной план сотрудника.
        Если этап уже есть — обновляет planned_quantity.
        Возвращает планы на указанную дату.
        """
        try:
            # 1. Получаем/создаём DailyPlan для (date, employee_id)
            stmt_plan = select(self.model).where(
                self.model.date == date,
                self.model.employee_id == employee_id,
            )
            daily_plan = await self.session.scalar(stmt_plan)

            if daily_plan is None:
                daily_plan = DailyPlan(
                    date=date,
                    employee_id=employee_id,
                )
                self.session.add(daily_plan)
                await self.session.flush()  # чтобы был id

            # 2. Ищем существующий DailyPlanStep
            stmt_step = select(DailyPlanStep).where(
                DailyPlanStep.daily_plan_id == daily_plan.id,
                DailyPlanStep.step_definition_id == step_id,
            )
            existing_step = await self.session.scalar(stmt_step)

            if existing_step is not None:
                existing_step.planned_quantity = planned_quantity
                self.session.add(existing_step)
            else:
                # 3. Если не нашли — создаём новый
                daily_plan_step = DailyPlanStep(
                    daily_plan_id=daily_plan.id,
                    step_definition_id=step_id,
                    planned_quantity=planned_quantity,
                )
                self.session.add(daily_plan_step)

            await self.session.flush()
            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise

        # 4. Возвращаем все планы на эту дату (как get)
        new_daily_plans = await self.get(date=date)
        return new_daily_plans
