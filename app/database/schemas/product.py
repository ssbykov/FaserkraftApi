from datetime import datetime
from typing import Optional, List, Type, ClassVar, TYPE_CHECKING
from zoneinfo import ZoneInfo

from pydantic import Field

from app.database import BaseSchema, Product
from app.database.models.product import ProductStatus
from app.database.schemas.process import ProcessRead, ProcessReadBase
from app.database.schemas.product_step import ProductStepRead


if TYPE_CHECKING:
    from app.database.schemas.packaging_box import PackagingBase

class ProductBase(BaseSchema):
    serial_number: str


class ProductCreate(ProductBase):
    process_id: int
    status: ProductStatus = ProductStatus.normal
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Europe/Moscow"))
    )
    packaging_id: int | None = None
    base_class: ClassVar[Type[Product]] = Product


class ProductRead(ProductBase):
    id: int
    work_process: ProcessRead
    created_at: datetime
    status: ProductStatus
    steps: Optional[List["ProductStepRead"]]
    packaging: Optional["PackagingBase"] = None

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }


class ProductShortRead(ProductBase):
    id: int
    work_process: ProcessReadBase
    status: ProductStatus

    class Config:
        from_attributes = True


class ProductsCountByLastStepRead(BaseSchema):
    """
    Статистика количества продуктов по процессу и последнему выполненному шагу.
    """

    process_id: int
    process_name: str
    step_definition_id: int
    step_name: str
    step_name_genitive: str
    count: int

    class Config:
        from_attributes = True

from app.database.schemas.packaging_box import PackagingBase
ProductRead.model_rebuild()
