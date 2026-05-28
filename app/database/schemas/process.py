from app.database import BaseSchema
from app.database.schemas.size_type import SizeType


class ProcessBase(BaseSchema):
    id: int
    name: str


class ProcessReadShort(ProcessBase):
    size_type: SizeType
