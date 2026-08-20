from pydantic import BaseModel

from app.database.schemas.daily_plan_step import DailyPlanStepRead


class StepCountStatRead(BaseModel):
    process_id: int
    process_name: str
    size_type_id: int | None = None
    size_type_name: str | None = None
    step_definition_id: int
    order: int
    step_name: str
    employee_id: int
    employee_name: str
    count: int


class ProcessCountStatRead(BaseModel):
    process_id: int
    process_name: str
    count: int


class EmployeePlanStatRead(BaseModel):
    employee_id: int
    employee_name: str
    working_days: int
    steps: list[DailyPlanStepRead]


class PeriodStatisticsRead(BaseModel):
    finished_products: list[ProcessCountStatRead]
    total_steps: list[StepCountStatRead]
    employee_plans: list[EmployeePlanStatRead]
