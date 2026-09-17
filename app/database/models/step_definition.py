from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.exc import DetachedInstanceError

from .base import BaseWithId

if TYPE_CHECKING:
    from .daily_plan_step import DailyPlanStep
    from .employee_norm_calculation import EmployeeNormCalculation
    from .process import Process
    from .product_step import ProductStep
    from .step_template import StepTemplate


class StepDefinition(BaseWithId):
    __tablename__ = "step_definitions"

    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    template_id: Mapped[int] = mapped_column(ForeignKey("step_templates.id"))
    order: Mapped[int]

    template: Mapped["StepTemplate"] = relationship(
        back_populates="definitions",
        lazy="selectin",
    )

    product_steps: Mapped[list["ProductStep"]] = relationship(
        back_populates="step_definition",
        lazy="selectin",
    )
    work_process: Mapped["Process"] = relationship(
        back_populates="steps",
        lazy="selectin",
    )

    steps: Mapped[list["DailyPlanStep"]] = relationship(
        back_populates="step_definition",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    norm_calculations: Mapped[list["EmployeeNormCalculation"]] = relationship(
        back_populates="step_definition",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return self.full_name

    @property
    def _process_label(self) -> str:
        state = inspect(self)
        # атрибут уже подгружен в память - можно безопасно читать без lazy load
        if "work_process" not in state.unloaded:
            try:
                return str(self.work_process)
            except DetachedInstanceError:
                pass
        return f"Процесс #{self.process_id}"

    @property
    def _template_label(self) -> str:
        state = inspect(self)
        if "template" not in state.unloaded:
            try:
                return str(self.template)
            except DetachedInstanceError:
                pass
        return f"Шаблон #{self.template_id}"

    @property
    def full_name(self) -> str:
        return f"{self._process_label}: {self._template_label}"
