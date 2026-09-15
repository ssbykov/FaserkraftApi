from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .step_definition import StepDefinition


class EmployeeNormCalculation(BaseWithId):
    __tablename__ = "employee_norm_calculations"

    step_definition_id: Mapped[int] = mapped_column(
        ForeignKey("step_definitions.id"), index=True
    )
    date: Mapped[date] = mapped_column(
        Date, server_default=func.current_date()
    )
    salary_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    difficulty_coefficient: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    daily_norm: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    step_definition: Mapped["StepDefinition"] = relationship(
        back_populates="norm_calculations",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"{self.date}: {self.salary_rate} руб. "
            f"(коэф. {self.difficulty_coefficient})"
        )

    @property
    def calculated_norm(self) -> Decimal | None:
        """Итоговая среднедневная норма в рублях с учетом коэффициента сложности."""
        if self.daily_norm:
            return (self.salary_rate / self.daily_norm) * self.difficulty_coefficient
        return None