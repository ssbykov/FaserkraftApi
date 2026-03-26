from app.database import BaseSchema


class StepTemplateRead(BaseSchema):
    name: str
    name_genitive: str

    model_config = {"from_attributes": True}
