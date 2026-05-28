from datetime import datetime

from app.database import BaseSchema
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.detailed import (
    StepDefinitionReadWithProcess,
    ProductInventoryItem,
)

# ---------- Inventory ----------


class InventoryRead(BaseSchema):
    id: int
    created_by: EmployeeRead
    created_at: datetime
    completed_at: datetime | None


class InventoryListItemOut(BaseSchema):
    id: int
    created_at: datetime
    completed_at: datetime | None
    created_by_id: int
    item_count: int


# ---------- InventoryItem ----------


class InventoryItemRead(BaseSchema):
    id: int
    inventory_id: int
    serial_number: str
    step_definition: StepDefinitionReadWithProcess
    scanned_at: datetime


class AddInventoryItemRequest(BaseSchema):
    serial_number: str
    step_definition_id: int


# ---------- Compare ----------


class InventoryCompareResultRead(BaseSchema):
    db_count: int
    scanned_count: int
    matched: list[ProductInventoryItem]
    missing: list[ProductInventoryItem]
    unexpected: list[ProductInventoryItem]
