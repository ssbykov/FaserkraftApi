from datetime import datetime
from typing import List, ClassVar, Type
from zoneinfo import ZoneInfo

from pydantic import Field

from app.database import BaseSchema
from app.database.models import Packaging
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.product import ProductsFinishedRead


class PackagingBase(BaseSchema):
    serial_number: str

    model_config = {"from_attributes": True}

class PackagingCreate(PackagingBase):
    performed_by_id: int = None

    base_class: ClassVar[Type[Packaging]] = Packaging

    class Config:
        from_attributes = True

class PackagingCreateWithProducts(PackagingBase):
    products: List[int]

class PackagingRead(PackagingCreate):
    id: int
    performed_by: EmployeeRead
    products: List[ProductsFinishedRead]

    class Config:
        from_attributes = True
