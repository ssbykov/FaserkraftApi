from datetime import datetime
from typing import Type
from zoneinfo import ZoneInfo

from pydantic import Field

from app.database import BaseSchema, Product, BaseWithId


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

    model_config = {"from_attributes": True}
