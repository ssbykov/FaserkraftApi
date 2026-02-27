from app.database import BaseSchema


class StepTemplateRead(BaseSchema):
    name: str

    model_config = {"from_attributes": True}
