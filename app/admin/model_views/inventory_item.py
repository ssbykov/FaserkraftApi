from app.admin.custom_model_view import CustomModelView
from app.database.crud.inventory_item import InventoryItemRepository
from app.database.models import InventoryItem


class InventoryItemAdmin(
    CustomModelView[InventoryItem],
    model=InventoryItem,
):
    repo_type = InventoryItemRepository
    name_plural = "Позиции инвентаризации"
    name = "Позиция инвентаризации"
    category = "Склад"

    column_list = ("inventory_id", "serial_number", "step_definition", "scanned_at")

    # убираем из detail view лишние поля
    column_details_exclude_list = ("id", "step_definition_id", "inventory_id")

    column_searchable_list = ("serial_number",)

    column_labels = {
        "inventory": "Инвентаризация",
        "inventory_id": "Инвентаризация (ID)",
        "serial_number": "Серийный номер",
        "step_definition": "Этап",
        "step_definition_id": "Этап (ID)",
        "scanned_at": "Время сканирования",
    }

    column_formatters = {
        "step_definition": lambda m, a: (
            m.step_definition.full_name if m.step_definition else "—"
        ),
    }

    column_formatters_detail = {
        "step_definition": lambda m, a: (
            m.step_definition.full_name if m.step_definition else "—"
        ),
    }

    can_export = False
