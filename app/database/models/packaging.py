from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from .base import BaseWithId


class Packaging(BaseWithId):
    __tablename__ = "packaging"

    serial_number = Column(String, unique=True, nullable=False)

    products = relationship(
        "Product",
        back_populates="packaging",
        lazy="selectin",
    )

    def __repr__(self):
        return self.serial_number

