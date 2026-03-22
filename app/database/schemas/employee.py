from app.database import BaseSchema
from database.schemas.user import UserRead


class EmployeeRead(BaseSchema):
    id: int
    name: str
    user: UserRead

    model_config = {"from_attributes": True}
