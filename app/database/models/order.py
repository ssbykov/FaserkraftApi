from sqlalchemy import Column, String, Date, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import BaseWithId


class Order(BaseWithId):
    __tablename__ = "orders"

    contract_number = Column(String, nullable=False)
    contract_date = Column(Date, nullable=False)
    planned_shipment_date = Column(Date, nullable=True)
    shipment_date = Column(Date, nullable=True)
    shipment_by_id = Column(ForeignKey("employees.id"), nullable=True)

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="OrderItem.id",
    )

    packaging = relationship(
        "Packaging",
        back_populates="order",
        lazy="selectin",
    )

    shipment_by = relationship(
        "Employee",
        foreign_keys=[shipment_by_id],
        lazy="selectin",
    )

    def __repr__(self):
        return f"Order {self.contract_number} from {self.contract_date}"


class OrderItem(BaseWithId):
    __tablename__ = "order_items"

    order_id = Column(ForeignKey("orders.id"), nullable=False)
    process_id = Column(ForeignKey("processes.id"), nullable=False)
    quantity = Column(Integer, nullable=False)

    order = relationship(
        "Order",
        back_populates="items",
    )

    work_process = relationship(
        "Process",
        back_populates="order_items",
        lazy="selectin",
    )

    def __repr__(self):
        return f"{self.work_process} x {self.quantity}"