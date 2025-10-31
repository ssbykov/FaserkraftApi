from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import BaseWithId


class StepDefinition(BaseWithId):
    __tablename__ = "step_definitions"

    process_id = Column(ForeignKey("processes.id"), nullable=False)
    template_id = Column(ForeignKey("step_templates.id"), nullable=False)
    order = Column(Integer, nullable=False)

    template = relationship("StepTemplate", back_populates="definitions")
    product_steps = relationship("ProductStep", back_populates="step_definition")

    def __repr__(self):
        return f"{self.order}: id шаблона {self.template_id}"
