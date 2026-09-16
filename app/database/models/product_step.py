from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .employee import Employee
    from .product import Product
    from .step_definition import StepDefinition


class StepStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    done = "done"

    @property
    def label(self) -> str:
        labels = {
            StepStatus.pending: "⏳",
            StepStatus.accepted: "🛠️",
            StepStatus.done: "✔️",
        }
        return labels.get(self, self.value)


class ProductStep(BaseWithId):
    __tablename__ = "product_steps"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    step_definition_id: Mapped[int] = mapped_column(ForeignKey("step_definitions.id"))

    status: Mapped[StepStatus] = mapped_column(
        SqlEnum(StepStatus, name="step_status_enum"),
        default=StepStatus.pending,
    )

    accepted_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"))
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    performed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"))
    performed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    product: Mapped["Product"] = relationship(back_populates="steps")
    step_definition: Mapped["StepDefinition"] = relationship(
        back_populates="product_steps",
        lazy="selectin",
    )

    accepted_by: Mapped[Optional["Employee"]] = relationship(
        foreign_keys=[accepted_by_id],
        back_populates="product_steps_accepted",
    )
    performed_by: Mapped[Optional["Employee"]] = relationship(
        foreign_keys=[performed_by_id],
        back_populates="product_steps_performed",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"{self.step_definition} - {self.status.label}"
