from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .step_definition import StepDefinition


class StepTemplate(BaseWithId):
    __tablename__ = "step_templates"

    name: Mapped[str] = mapped_column(String, unique=True)
    name_genitive: Mapped[str] = mapped_column(String, unique=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    definitions: Mapped[list["StepDefinition"]] = relationship(
        back_populates="template"
    )

    def __repr__(self) -> str:
        return self.name
