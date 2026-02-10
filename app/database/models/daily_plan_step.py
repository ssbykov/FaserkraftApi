from sqlalchemy import Column, Integer, ForeignKey, func, select
from sqlalchemy.orm import relationship, column_property

from .base import BaseWithId
from .product_step import StepStatus
from app.database.models import ProductStep, DailyPlan


class DailyPlanStep(BaseWithId):
    __tablename__ = "daily_plan_steps"

    daily_plan_id = Column(
        Integer,
        ForeignKey("daily_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_definition_id = Column(
        Integer,
        ForeignKey("step_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    planned_quantity = Column(Integer, nullable=False, default=0)

    actual_quantity = column_property(
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

    daily_plan = relationship(
        "DailyPlan",
        back_populates="steps",
        lazy="selectin",
    )

    step_definition = relationship(
        "StepDefinition",
        back_populates="steps",
        lazy="selectin",
    )

    @property
    def work_process(self):
        return f"{self.step_definition.work_process}"

    @property
    def date(self):
        return f"{self.daily_plan.date}"

    @property
    def employee_plan(self):
        return f"{self.daily_plan.employee.name}"

    def __repr__(self):
        return f"{self.step_definition} - {self.step_definition.work_process}, план: {self.planned_quantity} шт."
