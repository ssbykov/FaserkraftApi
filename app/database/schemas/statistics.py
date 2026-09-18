from decimal import Decimal

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
    template_id: int
    employee_id: int
    employee_name: str
    count: int
    total_amount: Decimal = Decimal("0")


class ProcessCountStatRead(BaseModel):
    process_id: int
    process_name: str
    count: int


class EmployeePlanStatRead(BaseModel):
    employee_id: int
    employee_name: str
    working_days: int
    steps: list[DailyPlanStepRead]


class EmployeeEarningsRead(BaseModel):
    employee_id: int
    employee_name: str
    total_earned: Decimal = Decimal("0")
    steps: list[StepCountStatRead]


class PeriodStatisticsRead(BaseModel):
    total_working_days: int = 0
    finished_products: list[ProcessCountStatRead] = []
    total_steps: list[StepCountStatRead] = []
    employee_plans: list[EmployeePlanStatRead] = []
    employee_earnings: list[EmployeeEarningsRead] = []
    first_half_earnings: list[EmployeeEarningsRead] = []
    total_earned_all: Decimal = Decimal("0")
