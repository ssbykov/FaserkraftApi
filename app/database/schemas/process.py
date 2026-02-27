from typing import List

from app.database import BaseSchema
from app.database.schemas.step_definition import StepDefinitionRead


class ProcessRead(BaseSchema):
    id: int
    name: str
    description: str | None = None
    steps: List[StepDefinitionRead]

    model_config = {"from_attributes": True}
