from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .daily_plan_step import DailyPlanStep
    from .employee import Employee


class DailyPlan(BaseWithId):
    __tablename__ = "daily_plans"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "date",
            name="uq_daily_plans_employee_date",
        ),
    )

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    date: Mapped[date] = mapped_column(Date)

    employee: Mapped["Employee"] = relationship(
        back_populates="plans",
        lazy="selectin",
    )
    steps: Mapped[list["DailyPlanStep"]] = relationship(
        back_populates="daily_plan",
        cascade="all, delete-orphan",
    )

    @property
    def planned_total(self) -> int:
        return sum(s.planned_quantity for s in self.steps)

    @property
    def actual_total(self) -> int:
        return sum(s.actual_quantity for s in self.steps)

    def __repr__(self) -> str:
        return f"{self.employee} - {self.date}"