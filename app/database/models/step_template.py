from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from .base import BaseWithId


class StepTemplate(BaseWithId):
    __tablename__ = "step_templates"

    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    definitions = relationship("StepDefinition", back_populates="template")

    def __repr__(self):
        return self.name
