from datetime import datetime

from app.database import BaseSchema
from app.database.schemas.detailed import StepDefinitionReadWithProcess
from app.database.schemas.employee import EmployeeRead
from database.models.product import ProductStatus

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


class ProductInventoryCompareItemRead(BaseSchema):
    id: int
    serial_number: str
    status: ProductStatus
    inventory_step_definition: StepDefinitionReadWithProcess | None
    accounting_step_definition: StepDefinitionReadWithProcess | None
    performed_at: datetime | None
