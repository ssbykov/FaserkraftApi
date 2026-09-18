from app.database import BaseSchema


class StepTemplateRead(BaseSchema):
    id: int
    name: str
    name_genitive: str