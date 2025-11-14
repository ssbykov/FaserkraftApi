from datetime import datetime
from typing import Optional

from app.database import BaseSchema
from app.database.models.product_step import StepStatus
from app.database.schemas.step_definition import StepDefinitionOut


class ProductStepBase(BaseSchema):
    id: int
    product_id: int
    status: StepStatus
    accepted_by_id: Optional[int]
    accepted_at: Optional[datetime]
    performed_by_id: Optional[int]
    performed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ProductStepOut(ProductStepBase):
    step_definition: StepDefinitionOut


class ProductStepUpdate(ProductStepBase):
    pass
