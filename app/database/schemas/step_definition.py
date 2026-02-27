from app.database import BaseSchema
from app.database.schemas.step_template import StepTemplateRead


class StepDefinitionRead(BaseSchema):
    id: int
    process_id: int
    order: int
    template: StepTemplateRead

    model_config = {"from_attributes": True}
