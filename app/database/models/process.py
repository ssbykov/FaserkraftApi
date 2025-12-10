from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from .base import BaseWithId


class Process(BaseWithId):
    __tablename__ = "processes"

    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    steps = relationship(
        "StepDefinition",
        back_populates="work_process",
        cascade="all, delete-orphan",
        order_by="StepDefinition.order",
        lazy="selectin",
    )

    products = relationship(
        "Product",
        back_populates="work_process",
        lazy="selectin",
    )

    def __repr__(self):
        return self.name
