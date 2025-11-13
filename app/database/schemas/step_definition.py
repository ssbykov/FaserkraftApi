from app.database import BaseSchema
from app.database.schemas.step_template import StepTemplateOut


class StepDefinitionOut(BaseSchema):
    id: int
    order: int
    template: StepTemplateOut

    model_config = {"from_attributes": True}
