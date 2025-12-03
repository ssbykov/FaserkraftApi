from datetime import datetime
from typing import Optional, List, Type, ClassVar
from zoneinfo import ZoneInfo

from pydantic import Field

from app.database import BaseSchema, Product
from app.database.schemas.process import ProcessRead
from app.database.schemas.product_step import ProductStepOut


class ProductBase(BaseSchema):
    serial_number: str


class ProductCreate(ProductBase):
    process_id: int
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Europe/Moscow"))
    )
    base_class: ClassVar[Type[Product]] = Product


class ProductCreateOut(ProductBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


class ProductRead(ProductBase):
    id: int
    process: ProcessRead
    created_at: datetime
    steps: Optional[List["ProductStepOut"]]

    model_config = {"from_attributes": True}
