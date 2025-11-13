from app.database import BaseSchema


class StepTemplateOut(BaseSchema):
    name: str

    model_config = {"from_attributes": True}
