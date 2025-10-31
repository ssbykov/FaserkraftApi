from sqlalchemy import Column, Integer, ForeignKey, Date, UniqueConstraint, Text
from sqlalchemy.orm import relationship

from .base import BaseWithId


class DailyPlan(BaseWithId):
    __tablename__ = "daily_plans"

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    planned_steps = Column(Integer, nullable=False, default=0)
    actual_steps = Column(Integer, nullable=False, default=0)

    employee = relationship("Employee", back_populates="plans")

    def __repr__(self):
        return (
            f"<DailyPlan(employee={self.employee_id}, "
            f"date={self.date.date() if self.date else None}, "
            f"plan={self.planned_steps}, fact={self.actual_steps})>"
        )
