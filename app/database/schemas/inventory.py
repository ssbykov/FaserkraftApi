from datetime import datetime

from app.database import BaseSchema
from app.database.schemas.employee import EmployeeRead


# ---------- Inventory ----------


class InventoryRead(BaseSchema):
    id: int
    created_by: EmployeeRead
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


# ---------- InventoryItem ----------


class InventoryItemRead(BaseSchema):
    id: int
    inventory_id: int
    serial_number: str
    step_definition_id: int
    scanned_at: datetime

    class Config:
        from_attributes = True


# ---------- Compare ----------


class InventoryCompareResultRead(BaseSchema):
    """
    Результат сверки отсканированных позиций с учётными данными
    по одному этапу технологического процесса.
    """

    step_definition_id: int
    step_name: str | None
    process_id: int | None
    db_count: int
    scanned_count: int
    matched: list[str]
    missing: list[str]  # в учёте есть, физически не найдены
    unexpected: list[str]  # физически найдены, в учёте нет
