from app.database import BaseSchema


class ProcessRead(BaseSchema):
    id: int
    name: str
    description: str

    model_config = {"from_attributes": True}
