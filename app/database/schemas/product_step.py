from datetime import datetime
from typing import Optional

from app.database import BaseSchema
from app.database.models.product_step import StepStatus
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.step_definition import StepDefinitionRead


class ProductStepBase(BaseSchema):
    id: int
    product_id: int
    status: StepStatus
    performed_by_id: Optional[int]
    performed_by: Optional[EmployeeRead]
    performed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ProductStepRead(ProductStepBase):
    step_definition: StepDefinitionRead
