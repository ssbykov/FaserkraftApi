from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from .base import BaseWithId
from .daily_plan import DailyPlan
from .product_step import ProductStep, StepStatus

if TYPE_CHECKING:
    from .step_definition import StepDefinition


class DailyPlanStep(BaseWithId):
    __tablename__ = "daily_plan_steps"

    daily_plan_id: Mapped[int] = mapped_column(
        ForeignKey("daily_plans.id", ondelete="CASCADE")
    )
    step_definition_id: Mapped[int] = mapped_column(
        ForeignKey("step_definitions.id", ondelete="RESTRICT")
    )

    planned_quantity: Mapped[int] = mapped_column(default=0)

    actual_quantity: Mapped[int] = column_property(
        select(func.count(ProductStep.id))
        .where(
            ProductStep.step_definition_id == step_definition_id,
            ProductStep.performed_by_id == DailyPlan.employee_id,
            func.date(ProductStep.performed_at) == DailyPlan.date,
            ProductStep.status == StepStatus.done,
        )
        .correlate_except(ProductStep)
        .scalar_subquery()
    )

    daily_plan: Mapped["DailyPlan"] = relationship(
        back_populates="steps",
        lazy="selectin",
    )

    step_definition: Mapped["StepDefinition"] = relationship(
        back_populates="steps",
        lazy="selectin",
    )

    @property
    def work_process(self) -> str:
        return f"{self.step_definition.work_process}"

    @property
    def date(self) -> str:
        return f"{self.daily_plan.date}"

    @property
    def employee_plan(self) -> str:
        return f"{self.daily_plan.employee.name}"

    def __repr__(self) -> str:
        return (
            f"{self.step_definition} - {self.step_definition.work_process}, "
            f"план: {self.planned_quantity} шт."
        )
