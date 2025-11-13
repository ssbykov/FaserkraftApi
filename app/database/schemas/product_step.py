from datetime import datetime
from typing import Optional

from app.database import BaseSchema
from app.database.models.product_step import StepStatus
from app.database.schemas.step_definition import StepDefinitionOut


class ProductStepOut(BaseSchema):
    id: int
    product_id: int
    step_definition: StepDefinitionOut
    status: StepStatus
    accepted_by_id: Optional[int]
    accepted_at: Optional[datetime]
    performed_by_id: Optional[int]
    performed_at: Optional[datetime]

    model_config = {"from_attributes": True}
