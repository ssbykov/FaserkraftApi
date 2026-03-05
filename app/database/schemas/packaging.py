from datetime import datetime
from typing import List, ClassVar, Type
from zoneinfo import ZoneInfo

from pydantic import Field
from sqlalchemy import null

from app.database import BaseSchema
from app.database.models import Packaging


class PackagingBase(BaseSchema):
    serial_number: str

    model_config = {"from_attributes": True}

class PackagingCreate(PackagingBase):
    performed_by_id: int = None
    performed_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Europe/Moscow"))
    )

    base_class: ClassVar[Type[Packaging]] = Packaging

    class Config:
        from_attributes = True

class PackagingCreateWithProducts(PackagingCreate):
    products: List[int]

class PackagingRead(PackagingCreate):
    id: int

    class Config:
        from_attributes = True
