from sqlalchemy import Column, Integer, ForeignKey, Date
from sqlalchemy.orm import relationship

from .base import BaseWithId


class DailyPlan(BaseWithId):
    __tablename__ = "daily_plans"

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)

    employee = relationship("Employee", back_populates="plans")
    steps = relationship(
        "DailyPlanStep",
        back_populates="daily_plan",
        cascade="all, delete-orphan",
    )

    @property
    def planned_total(self) -> int:
        return sum(s.planned_quantity for s in self.steps)

    @property
    def actual_total(self) -> int:
        return sum(s.actual_quantity for s in self.steps)

    def __repr__(self):
        return f"План: на {self.date}, сотрудник {self.employee_id}"
