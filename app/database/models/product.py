from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    func,
)
from enum import Enum
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SqlEnum

from .base import BaseWithId


class ProductStatus(str, Enum):
    normal = "normal"
    scrap = "scrap"
    rework = "rework"

    @property
    def label(self):
        labels = {
            ProductStatus.normal: "🟢",
            ProductStatus.rework: "🟡",
            ProductStatus.scrap: "🔴",
        }
        return labels.get(self, self.value)

class Product(BaseWithId):
    __tablename__ = "products"

    serial_number = Column(String, unique=True, nullable=False)
    process_id = Column(ForeignKey("processes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    status = Column(
        SqlEnum(ProductStatus, name="product_status_enum", native_enum=True),
        nullable=False,
        server_default=ProductStatus.normal.value,
    )

    work_process = relationship("Process", back_populates="products")
    steps = relationship(
        "ProductStep",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductStep.id",
        lazy="selectin",
    )

    def __repr__(self):
        return self.serial_number
