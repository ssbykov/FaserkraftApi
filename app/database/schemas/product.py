from datetime import datetime
from typing import Optional, List, Type, ClassVar
from zoneinfo import ZoneInfo

from pydantic import Field

from app.database import BaseSchema, Product
from app.database.models.product import ProductStatus
from app.database.schemas.process import ProcessRead, ProcessReadBase
from app.database.schemas.product_step import ProductStepRead


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
    packaging_id: int | None

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }


class ProductsFinishedRead(ProductBase):
    id: int
    work_process: ProcessReadBase

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
