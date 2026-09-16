from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .employee import Employee
    from .step_definition import StepDefinition


class Inventory(BaseWithId):
    """Сеанс — просто "открытая инвентаризация", без привязки к этапу."""

    __tablename__ = "inventories"

    created_by_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_by: Mapped["Employee"] = relationship(
        foreign_keys=[created_by_id],
        back_populates="inventory",
        lazy="selectin",
    )

    items: Mapped[list["InventoryItem"]] = relationship(
        back_populates="inventory",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Инвентаризация ID: {self.id} от {self.created_at}"


class InventoryItem(BaseWithId):
    """Строка — несёт всю информацию о том, где физически найдено изделие."""

    __tablename__ = "inventory_items"

    __table_args__ = (
        UniqueConstraint("inventory_id", "serial_number", name="uq_inventory_serial"),
    )

    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"))
    serial_number: Mapped[str] = mapped_column(String)
    step_definition_id: Mapped[int] = mapped_column(ForeignKey("step_definitions.id"))
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    inventory: Mapped["Inventory"] = relationship(
        back_populates="items",
        lazy="selectin",
    )
    step_definition: Mapped["StepDefinition"] = relationship(
        foreign_keys=[step_definition_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Серийный номер: {self.serial_number}"
