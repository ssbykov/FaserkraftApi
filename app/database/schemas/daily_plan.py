from datetime import date
from typing import ClassVar, List, Optional, Type

from app.database import DailyPlan, BaseSchema
from app.database.schemas.daily_plan_step import DailyPlanStepRead
from app.database.schemas.employee import EmployeeRead


class DailyPlanBase(BaseSchema):
    employee_id: int
    date: date


class DailyPlanCreate(DailyPlanBase):
    base_class: ClassVar[Type[DailyPlan]] = DailyPlan


class DailyPlanRead(DailyPlanBase):
    id: int
    employee: EmployeeRead
    steps: Optional[List["DailyPlanStepRead"]]

    model_config = {"from_attributes": True}
