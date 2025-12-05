from app.database import BaseSchema


class EmployeeRead(BaseSchema):
    id: int
    name: str

    model_config = {"from_attributes": True}
