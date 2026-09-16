from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .order import OrderItem
    from .product import Product
    from .size_type import SizeType
    from .step_definition import StepDefinition


class Process(BaseWithId):
    __tablename__ = "processes"

    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    size_type_id: Mapped[Optional[int]] = mapped_column(ForeignKey("size_type.id"))

    size_type: Mapped[Optional["SizeType"]] = relationship(
        back_populates="work_process",
        lazy="selectin",
    )

    steps: Mapped[list["StepDefinition"]] = relationship(
        back_populates="work_process",
        cascade="all, delete-orphan",
        order_by="StepDefinition.order",
        lazy="selectin",
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="work_process",
        lazy="selectin",
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="work_process",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return self.name
