from datetime import datetime
from typing import List, ClassVar, Type, TYPE_CHECKING

from app.database import BaseSchema
from app.database.models import Packaging
from app.database.schemas.employee import EmployeeRead

if TYPE_CHECKING:
    from app.database.schemas.product import ProductShortRead


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
    performed_at: datetime
    products: List["ProductShortRead"]
    order_id: int | None

    class Config:
        from_attributes = True


from app.database.schemas.product import ProductShortRead

PackagingRead.model_rebuild()
