from enum import Enum

from sqlalchemy import (
    Column,
    ForeignKey,
    DateTime,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import relationship

from .base import BaseWithId


class StepStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    done = "done"

    @property
    def label(self):
        labels = {
            StepStatus.pending: "⏳",
            StepStatus.accepted: "🛠️",
            StepStatus.done: "✔️",
        }
        return labels.get(self, self.value)


class ProductStep(BaseWithId):
    __tablename__ = "product_steps"

    product_id = Column(ForeignKey("products.id"), nullable=False)
    step_definition_id = Column(ForeignKey("step_definitions.id"), nullable=False)

    status = Column(
        SqlEnum(StepStatus, name="step_status_enum"),
        default=StepStatus.pending,
        nullable=False,
    )

    accepted_by_id = Column(ForeignKey("employees.id"), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    performed_by_id = Column(ForeignKey("employees.id"), nullable=True)
    performed_at = Column(DateTime(timezone=True), nullable=True)

    product = relationship("Product", back_populates="steps")
    step_definition = relationship(
        "StepDefinition", back_populates="product_steps", lazy="selectin"
    )

    accepted_by = relationship(
        "Employee",
        foreign_keys=[accepted_by_id],
        back_populates="product_steps_accepted",
    )
    performed_by = relationship(
        "Employee",
        foreign_keys=[performed_by_id],
        back_populates="product_steps_performed",
    )

    def __repr__(self):
        return f"{self.step_definition} - {self.status.label}"
