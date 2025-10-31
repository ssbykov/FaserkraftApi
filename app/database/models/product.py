from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship

from .base import BaseWithId


class Product(BaseWithId):
    __tablename__ = "products"

    serial_number = Column(String, unique=True, nullable=False)
    process_id = Column(ForeignKey("processes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    process = relationship("Process", back_populates="products")
    steps = relationship(
        "ProductStep",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductStep.id",
    )

    def __repr__(self):
        return (
            f"<Product(serial_number={self.serial_number}, process={self.process_id})>"
        )
