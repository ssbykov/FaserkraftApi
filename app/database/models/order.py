from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .employee import Employee
    from .packaging_box import Packaging
    from .process import Process


class Order(BaseWithId):
    __tablename__ = "orders"

    contract_number: Mapped[str] = mapped_column(String)
    contract_date: Mapped[date] = mapped_column(Date)
    planned_shipment_date: Mapped[date] = mapped_column(Date)
    shipment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    shipment_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"))

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OrderItem.id",
    )

    packaging: Mapped[list["Packaging"]] = relationship(
        back_populates="order",
        lazy="selectin",
    )

    shipment_by: Mapped[Optional["Employee"]] = relationship(
        foreign_keys=[shipment_by_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Order {self.contract_number} from {self.contract_date}"


class OrderItem(BaseWithId):
    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    quantity: Mapped[int]

    order: Mapped["Order"] = relationship(back_populates="items")

    work_process: Mapped["Process"] = relationship(
        back_populates="order_items",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"{self.work_process} x {self.quantity}"