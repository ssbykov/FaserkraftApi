from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import BaseWithId


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

    # план по этому шагу на день
    planned_quantity = Column(Integer, nullable=False, default=0)

    # фактически сделано по этому шагу за день
    actual_quantity = Column(Integer, nullable=False, default=0)

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
