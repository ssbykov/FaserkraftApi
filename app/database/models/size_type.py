from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .process import Process


class SizeType(BaseWithId):
    __tablename__ = "size_type"

    name: Mapped[str] = mapped_column(String, unique=True)
    packaging_count: Mapped[int]

    work_process: Mapped[list["Process"]] = relationship(
        back_populates="size_type",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return self.name