from typing import ClassVar, Type

from app.database import BaseSchema
from app.database.models import DailyPlanStep
from app.database.schemas.step_definition import StepDefinitionRead


class DailyPlanStepBase(BaseSchema):
    daily_plan_id: int
    step_definition_id: int
    planned_quantity: int = 0
    actual_quantity: int = 0


class DailyPlanStepCreate(DailyPlanStepBase):
    base_class: ClassVar[Type[DailyPlanStep]] = DailyPlanStep


class DailyPlanStepRead(DailyPlanStepBase):
    id: int
    work_process: str
    step_definition: StepDefinitionRead

    model_config = {"from_attributes": True}
