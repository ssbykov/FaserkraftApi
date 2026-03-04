from typing import List

from app.database import BaseSchema


class PackagingBase(BaseSchema):
    serial_number: str

    model_config = {"from_attributes": True}

class PackagingCreate(PackagingBase):
    products: List[int] | None = None

class PackagingRead(PackagingCreate):
    id: int
