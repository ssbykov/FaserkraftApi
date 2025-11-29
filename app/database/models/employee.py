from enum import Enum

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import BaseWithId


class Role(str, Enum):
    admin = "admin"
    worker = "worker"


class Employee(BaseWithId):
    __tablename__ = "employees"

    name = Column(String, nullable=False, unique=True)
    role = Column(SqlEnum(Role, name="role_enum"), nullable=False, default=Role.worker)
    telegram_id: Mapped[int] = mapped_column(String, nullable=True, unique=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=True, unique=True
    )
    user = relationship("User", uselist=False, back_populates=None, viewonly=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id"), nullable=True, unique=True
    )
    device = relationship("Device", back_populates=None, viewonly=True)

    plans = relationship("DailyPlan", back_populates="employee")
    product_steps_performed = relationship(
        "ProductStep",
        back_populates="performed_by",
        foreign_keys="ProductStep.performed_by_id",
    )
    product_steps_accepted = relationship(
        "ProductStep",
        back_populates="accepted_by",
        foreign_keys="ProductStep.accepted_by_id",
    )

    def __repr__(self):
        return self.name
