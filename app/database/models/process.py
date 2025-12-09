from sqlalchemy import Column, Integer, String, Text
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
    )

    products = relationship("Product", back_populates="work_process")

    def __repr__(self):
        return self.name
