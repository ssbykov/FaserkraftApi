from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from .base import BaseWithId


class Packaging(BaseWithId):
    __tablename__ = "packaging"

    serial_number = Column(String, unique=True, nullable=False)

    performed_by_id = Column(ForeignKey("employees.id"), nullable=True)
    performed_at = Column(DateTime(timezone=True), nullable=True)

    products = relationship(
        "Product",
        back_populates="packaging",
        lazy="selectin",
    )
    performed_by = relationship(
        "Employee",
        foreign_keys=[performed_by_id],
        back_populates="packaging_performed",
        lazy="selectin",
    )


    def __repr__(self):
        return self.serial_number

