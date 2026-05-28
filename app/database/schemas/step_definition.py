from app.database import BaseSchema
from app.database.schemas.step_template import StepTemplateRead


class StepDefinitionBase(BaseSchema):
    id: int
    order: int
    template: StepTemplateRead


class StepDefinitionRead(StepDefinitionBase):
    process_id: int
