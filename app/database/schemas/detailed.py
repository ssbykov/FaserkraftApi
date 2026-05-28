from typing import List

from app.database.models.product import ProductStatus
from app.database.schemas.process import ProcessBase, ProcessReadShort
from app.database.schemas.step_definition import StepDefinitionBase, StepDefinitionRead
from database import BaseSchema


class ProcessRead(ProcessReadShort):
    description: str | None = None
    steps: List[StepDefinitionRead]


class StepDefinitionReadWithProcess(StepDefinitionBase):
    work_process: ProcessBase


class ProductInventoryItem(BaseSchema):
    id: int
    serial_number: str
    status: ProductStatus
    step_definition: StepDefinitionReadWithProcess
