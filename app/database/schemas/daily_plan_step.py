from datetime import date as date_type

from sqlalchemy.orm import Mapped

from app.database import BaseSchema
from app.database.schemas.step_definition import StepDefinitionRead


class DailyPlanStepBase(BaseSchema):
    daily_plan_id: int
    step_definition_id: int
    planned_quantity: int = 0
    actual_quantity: int = 0


class DailyPlanStepCreate(BaseSchema):
    employee_id: int
    plan_date: date_type
    step_id: int
    planned_quantity: int


class DailyPlanStepUpdate(DailyPlanStepCreate):
    step_definition_id: int


class DailyPlanStepRead(DailyPlanStepBase):
    id: int
    work_process: str
    step_definition: StepDefinitionRead

    model_config = {"from_attributes": True}
