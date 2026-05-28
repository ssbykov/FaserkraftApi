from app.database import BaseSchema


class SizeType(BaseSchema):
    id: int
    name: str
    packaging_count: int
