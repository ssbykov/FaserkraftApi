from datetime import date

from pydantic import Field

from app.database import BaseSchema
from app.database.schemas.employee import EmployeeRead
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
    planned_shipment_date: date
    shipment_date: date | None = None
    shipment_by: EmployeeRead | None = None
    items: list[OrderItemRead] = Field(default_factory=list)
    packaging: list[PackagingRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrderItemCreate(BaseSchema):
    process_id: int
    quantity: int


class OrderCreate(BaseSchema):
    contract_number: str
    contract_date: date
    planned_shipment_date: date

class OrderUpdate(OrderCreate):
    id: int

class OrderClose(BaseSchema):
    shipment_date: date
    shipment_by_id: int