from datetime import datetime
from typing import Type, Optional, List
from zoneinfo import ZoneInfo

from pydantic import Field

from app.database import BaseSchema, Product, BaseWithId
from app.database.schemas.product_step import ProductStepOut


class ProductBase(BaseSchema):
    serial_number: str
    process_id: int


class ProductCreate(ProductBase):
    base_class: Type["BaseWithId"] = Field(default=Product, exclude=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Europe/Moscow"))
    )


class ProductRead(ProductBase):
    id: int
    created_at: datetime
    steps: Optional[List[ProductStepOut]]

    model_config = {"from_attributes": True}
