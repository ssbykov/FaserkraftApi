from typing import List

from app.database import BaseSchema
from app.database.schemas.size_type import SizeType
from app.database.schemas.step_definition import StepDefinitionRead

class ProcessReadBase(BaseSchema):
    id: int
    name: str
    size_type: SizeType
    model_config = {"from_attributes": True}



class ProcessRead(ProcessReadBase):
    description: str | None = None
    steps: List[StepDefinitionRead]

    model_config = {"from_attributes": True}
