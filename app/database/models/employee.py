from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .daily_plan import DailyPlan
    from .device import Device
    from .inventory import Inventory
    from .packaging_box import Packaging
    from .product_step import ProductStep
    from .user import User


class Role(str, Enum):
    admin = "admin"
    master = "master"
    worker = "worker"


class Employee(BaseWithId):
    __tablename__ = "employees"

    name: Mapped[str] = mapped_column(String, unique=True)
    role: Mapped[Role] = mapped_column(
        SqlEnum(Role, name="role_enum"), default=Role.worker
    )
    telegram_id: Mapped[Optional[str]] = mapped_column(String, unique=True)

    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), unique=True
    )
    user: Mapped[Optional["User"]] = relationship(
        uselist=False,
        viewonly=True,
        lazy="selectin",
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("devices.id"), unique=True
    )
    device: Mapped[Optional["Device"]] = relationship(back_populates="employee")

    plans: Mapped[list["DailyPlan"]] = relationship(back_populates="employee")
    product_steps_performed: Mapped[list["ProductStep"]] = relationship(
        back_populates="performed_by",
        foreign_keys="ProductStep.performed_by_id",
    )
    product_steps_accepted: Mapped[list["ProductStep"]] = relationship(
        back_populates="accepted_by",
        foreign_keys="ProductStep.accepted_by_id",
    )
    packaging_performed: Mapped[list["Packaging"]] = relationship(
        back_populates="performed_by",
        foreign_keys="Packaging.performed_by_id",
    )
    inventory: Mapped[list["Inventory"]] = relationship(
        back_populates="created_by",
        foreign_keys="Inventory.created_by_id",
    )

    def __repr__(self) -> str:
        return self.name