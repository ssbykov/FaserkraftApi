from app.database import BaseSchema
from database.models.employee import Role
from database.schemas.user import UserRead


class EmployeeRead(BaseSchema):
    id: int
    name: str
    user: UserRead
    role: Role
