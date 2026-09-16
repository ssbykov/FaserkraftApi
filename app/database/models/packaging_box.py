from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .employee import Employee
    from .order import Order
    from .product import Product


class Packaging(BaseWithId):
    __tablename__ = "packaging"

    serial_number: Mapped[str] = mapped_column(String, unique=True)

    performed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"))
    performed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    shipment_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"))
    shipment_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"))

    products: Mapped[list["Product"]] = relationship(
        back_populates="packaging",
        lazy="selectin",
    )

    performed_by: Mapped[Optional["Employee"]] = relationship(
        foreign_keys=[performed_by_id],
        back_populates="packaging_performed",
        lazy="selectin",
    )

    shipment_by: Mapped[Optional["Employee"]] = relationship(
        foreign_keys=[shipment_by_id],
        lazy="selectin",
    )

    order: Mapped[Optional["Order"]] = relationship(
        back_populates="packaging",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return self.serial_number
