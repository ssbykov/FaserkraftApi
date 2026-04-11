from datetime import date

from pydantic import Field

from app.database import BaseSchema
from app.database.schemas.packaging_box import PackagingRead
from app.database.schemas.process import ProcessReadBase


class OrderItemRead(BaseSchema):
    id: int
    quantity: int
    work_process: ProcessReadBase

    model_config = {"from_attributes": True}


class OrderRead(BaseSchema):
    id: int
    contract_number: str
    contract_date: date
    planned_shipment_date: date | None = None
    items: list[OrderItemRead] = Field(default_factory=list)
    packaging: list[PackagingRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}
