from sqlalchemy import Column, ForeignKey, DateTime, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseWithId


# Сеанс — просто "открытая инвентаризация", без привязки к этапу
class Inventory(BaseWithId):
    __tablename__ = "inventories"

    created_by_id = Column(ForeignKey("employees.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_by = relationship(
        "Employee",
        foreign_keys=[created_by_id],
        back_populates="inventory",
        lazy="selectin",
    )

    items = relationship(
        "InventoryItem",
        back_populates="inventory",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"Инвентаризация ID: {self.id} от {self.created_at}"


# Строка — несёт всю информацию о том, где физически найдено изделие
class InventoryItem(BaseWithId):
    __tablename__ = "inventory_items"

    __table_args__ = (
        UniqueConstraint("inventory_id", "serial_number", name="uq_inventory_serial"),
    )

    inventory_id = Column(ForeignKey("inventories.id"), nullable=False)
    serial_number = Column(String, nullable=False)
    step_definition_id = Column(ForeignKey("step_definitions.id"), nullable=False)
    scanned_at = Column(DateTime(timezone=True), nullable=False)

    inventory = relationship(
        "Inventory",
        back_populates="items",
        lazy="selectin",
    )
    step_definition = relationship(
        "StepDefinition",
        foreign_keys=[step_definition_id],
        lazy="selectin",
    )

    def __repr__(self):
        return f"Серийный номер: {self.serial_number}"

