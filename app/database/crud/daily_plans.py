from collections import defaultdict
from datetime import date as date_type
from typing import Sequence

from sqlalchemy import select, exists, func, distinct
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload

from app.database import DailyPlan, SessionDep, StepDefinition, ProductStep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import DailyPlanStep


def get_daily_plan_repo(session: SessionDep) -> "DailyPlanRepository":
    return DailyPlanRepository(session)


class DailyPlanRepository(GetBackNextIdMixin[DailyPlan]):
    model = DailyPlan

    async def _get_or_create_daily_plan(
        self, date: date_type, employee_id: int
    ) -> DailyPlan:
        """Получить или создать DailyPlan для сотрудника на указанную дату."""
        stmt = select(self.model).where(
            self.model.date == date,
            self.model.employee_id == employee_id,
        )
        daily_plan = await self.session.scalar(stmt)

        if daily_plan is None:
            daily_plan = DailyPlan(date=date, employee_id=employee_id)
            self.session.add(daily_plan)
            await self.session.flush()

        return daily_plan

    async def _handle_operation(
        self, operation, date: date_type
    ) -> Sequence[DailyPlan]:
        """Обертка для выполнения операций с транзакцией + возврат актуальных планов."""
        try:
            await operation()
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # всегда возвращаем актуальные планы на дату
        return await self.get(date=date)

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
        employee_id: int,
        step_def_id: int,
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
        return bool(await self.session.scalar(select(exists(subq))))

    async def check_step_in_daily_plan(
        self,
        *,
        date: date_type,
        employee_id: int,
        product_step_id: int,
    ) -> bool:
        step_def_id = await self._get_step_def(product_step_id)
        return step_def_id is not None and await self.check_step_def_in_daily_plan(
            date=date, employee_id=employee_id, step_def_id=step_def_id
        )

    async def _get_step_def(self, product_step_id: int) -> int | None:
        stmt = select(ProductStep.step_definition_id).where(
            ProductStep.id == product_step_id
        )
        return await self.session.scalar(stmt)

    async def add_step_to_daily_plan(
        self,
        *,
        date: date_type,
        employee_id: int,
        step_id: int,
        planned_quantity: int = 0,
    ) -> Sequence[DailyPlan]:
        async def operation():
            daily_plan = await self._get_or_create_daily_plan(date, employee_id)

            stmt = select(DailyPlanStep).where(
                DailyPlanStep.daily_plan_id == daily_plan.id,
                DailyPlanStep.step_definition_id == step_id,
            )
            existing_step = await self.session.scalar(stmt)

            if existing_step:
                existing_step.planned_quantity = planned_quantity
            else:
                daily_plan_step = DailyPlanStep(
                    daily_plan_id=daily_plan.id,
                    step_definition_id=step_id,
                    planned_quantity=planned_quantity,
                )
                self.session.add(daily_plan_step)

        return await self._handle_operation(operation, date)

    async def update_step_in_daily_plan(
        self,
        *,
        step_id: int,
        date: date_type,
        employee_id: int,
        step_definition_id: int,
        planned_quantity: int,
    ) -> Sequence[DailyPlan]:
        async def operation():
            daily_plan = await self._get_or_create_daily_plan(date, employee_id)

            step_stmt = select(DailyPlanStep).where(DailyPlanStep.id == step_id)
            current_step = await self.session.scalar(step_stmt)

            if current_step is None:
                raise NoResultFound(f"DailyPlanStep id={step_id} not found")

            conflict_stmt = select(DailyPlanStep).where(
                DailyPlanStep.daily_plan_id == daily_plan.id,
                DailyPlanStep.step_definition_id == step_definition_id,
                DailyPlanStep.id != step_id,
            )
            conflict_step = await self.session.scalar(conflict_stmt)

            if conflict_step:
                conflict_step.planned_quantity = planned_quantity
                await self.session.delete(current_step)
            else:
                current_step.daily_plan_id = daily_plan.id
                current_step.step_definition_id = step_definition_id
                current_step.planned_quantity = planned_quantity

        return await self._handle_operation(operation, date)

    async def remove_step_from_daily_plan(
        self,
        *,
        daily_plan_step_id: int,
    ) -> Sequence[DailyPlan]:
        stmt = select(DailyPlanStep).where(DailyPlanStep.id == daily_plan_step_id)
        daily_plan_step = await self.session.scalar(stmt)

        if daily_plan_step is None:
            raise NoResultFound(f"DailyPlanStep id={daily_plan_step_id} not found")

        date = daily_plan_step.daily_plan.date

        async def operation():
            await self.session.delete(daily_plan_step)

        return await self._handle_operation(operation, date)

    async def copy_daily_plans_from_date(
        self,
        *,
        from_date: date_type,
        to_date: date_type | None = None,
    ) -> Sequence[DailyPlan]:
        to_date = to_date or date_type.today()

        if from_date == to_date:
            return await self.get(date=to_date)

        async def operation():
            source_stmt = (
                select(self.model)
                .options(joinedload(self.model.steps))
                .where(self.model.date == from_date)
            )
            source_result = await self.session.execute(source_stmt)
            source_plans = source_result.unique().scalars().all()

            target_stmt = select(self.model).where(self.model.date == to_date)
            target_result = await self.session.execute(target_stmt)
            target_plans = target_result.scalars().all()

            for target_plan in target_plans:
                steps_stmt = select(DailyPlanStep).where(
                    DailyPlanStep.daily_plan_id == target_plan.id
                )
                steps_result = await self.session.execute(steps_stmt)
                target_steps = steps_result.scalars().all()

                for step in target_steps:
                    await self.session.delete(step)

            for source_plan in source_plans:
                target_plan = await self._get_or_create_daily_plan(
                    to_date, source_plan.employee_id
                )

                for source_step in source_plan.steps:
                    self.session.add(
                        DailyPlanStep(
                            daily_plan_id=target_plan.id,
                            step_definition_id=source_step.step_definition_id,
                            planned_quantity=source_step.planned_quantity,
                        )
                    )

        return await self._handle_operation(operation, to_date)

    async def get_employee_plan_stats_by_period(
        self,
        date_from: date_type,
        date_to: date_type,
        employee_id: int | None = None,
    ) -> list[dict]:
        """
        Возвращает по каждому сотруднику:
        - количество рабочих дней (дней с планом) в периоде
        - суммарный planned_quantity за период
        - список DailyPlanStep за период (для детализации)
        """
        stmt = (
            select(self.model)
            .options(
                joinedload(self.model.employee),
                joinedload(self.model.steps)
                .joinedload(DailyPlanStep.step_definition)
                .joinedload(StepDefinition.template),
            )
            .where(
                self.model.date >= date_from,
                self.model.date <= date_to,
            )
            # только планы с хотя бы одним шагом
            .where(
                exists(
                    select(DailyPlanStep.id).where(
                        DailyPlanStep.daily_plan_id == self.model.id
                    )
                )
            )
        )

        if employee_id is not None:
            stmt = stmt.where(self.model.employee_id == employee_id)

        result = await self.session.execute(stmt)
        plans: Sequence[DailyPlan] = result.unique().scalars().all()

        # Группируем по сотруднику
        from collections import defaultdict

        grouped: dict[int, dict] = defaultdict(
            lambda: {
                "employee_name": "",
                "working_days": 0,
                "steps": [],
            }
        )

        for plan in plans:
            emp_id = plan.employee_id
            grouped[emp_id]["employee_name"] = plan.employee.name
            grouped[emp_id]["working_days"] += 1
            grouped[emp_id]["steps"].extend(plan.steps)

        return [
            {
                "employee_id": emp_id,
                **data,
            }
            for emp_id, data in grouped.items()
        ]

    async def get_working_days_count_by_period(
        self,
        date_from: date_type,
        date_to: date_type,
        employee_id: int | None = None,
    ) -> int:
        """
        Возвращает общее количество рабочих дней за указанный период.
        День считается рабочим, если на эту дату есть хотя бы один план
        с ненулевым количеством этапов (шагов).
        """
        stmt = select(func.count(distinct(self.model.date))).where(
            self.model.date >= date_from,
            self.model.date <= date_to,
            exists(
                select(DailyPlanStep.id).where(
                    DailyPlanStep.daily_plan_id == self.model.id
                )
            ),
        )

        if employee_id is not None:
            stmt = stmt.where(self.model.employee_id == employee_id)

        count = await self.session.scalar(stmt)
        return count or 0

    async def get_working_days_by_employee(
        self,
        date_from: date_type,
        date_to: date_type,
        employee_id: int | None = None,
    ) -> dict[int, set[date_type]]:
        """
        Возвращает по каждому employee_id множество дат, когда у него
        был план (DailyPlan с хотя бы одним DailyPlanStep) в периоде.
        Не привязано к конкретному step_definition_id.
        """
        stmt = (
            select(self.model.employee_id, self.model.date)
            .where(
                self.model.date >= date_from,
                self.model.date <= date_to,
                exists(
                    select(DailyPlanStep.id).where(
                        DailyPlanStep.daily_plan_id == self.model.id
                    )
                ),
            )
        )

        if employee_id is not None:
            stmt = stmt.where(self.model.employee_id == employee_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        working_days: dict[int, set[date_type]] = defaultdict(set)
        for emp_id, day in rows:
            working_days[emp_id].add(day)

        return working_days