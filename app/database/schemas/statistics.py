from pydantic import BaseModel


class StepCountStatRead(BaseModel):
    process_id: int
    process_name: str
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


class PeriodStatisticsRead(BaseModel):
    finished_products: list[ProcessCountStatRead]
    total_steps: list[StepCountStatRead]
