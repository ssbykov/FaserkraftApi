from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from .base import BaseWithId


class SizeType(BaseWithId):
    __tablename__ = "size_type"

    name = Column(String, unique=True, nullable=False)
    packaging_count = Column(Integer, nullable=False)

    work_process = relationship(
        "Process",
        back_populates="size_type",
        lazy="selectin",
    )

    def __repr__(self):
        return self.name
