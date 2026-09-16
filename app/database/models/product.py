from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .packaging_box import Packaging
    from .process import Process
    from .product_step import ProductStep


class ProductStatus(str, Enum):
    normal = "normal"
    scrap = "scrap"
    rework = "rework"

    @property
    def label(self) -> str:
        labels = {
            ProductStatus.normal: "🟢",
            ProductStatus.rework: "🟡",
            ProductStatus.scrap: "🔴",
        }
        return labels.get(self, self.value)


class Product(BaseWithId):
    __tablename__ = "products"

    serial_number: Mapped[str] = mapped_column(String, unique=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    status: Mapped[ProductStatus] = mapped_column(
        SqlEnum(ProductStatus, name="product_status_enum", native_enum=True),
        server_default=ProductStatus.normal.value,
    )

    packaging_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("packaging.id")
    )

    packaging: Mapped[Optional["Packaging"]] = relationship(
        back_populates="products", lazy="selectin"
    )

    work_process: Mapped["Process"] = relationship(back_populates="products")
    steps: Mapped[list["ProductStep"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductStep.id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return self.serial_number