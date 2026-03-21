from app.database import BaseSchema


class SizeType(BaseSchema):
    name: str
    packaging_count: int

    model_config = {"from_attributes": True}
