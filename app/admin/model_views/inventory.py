from datetime import datetime, timezone

from app.admin.custom_model_view import CustomModelView
from app.database.crud.inventory import InventoryRepository
from app.database.models import Inventory


class InventoryAdmin(
    CustomModelView[Inventory],
    model=Inventory,
):
    repo_type = InventoryRepository
    name_plural = "Инвентаризации"
    name = "Инвентаризация"
    category = "Склад"

    column_list = ("id", "created_by", "created_at", "completed_at")
    column_details_exclude_list = (
        "id",
        "created_by_id",
    )

    form_excluded_columns = ("created_at",)

    column_labels = {
        "created_by": "Создал (ID сотрудника)",
        "created_at": "Дата начала",
        "completed_at": "Дата завершения",
        "items": "Позиции",
    }

    can_export = False

    async def on_model_change(self, data: dict, model, is_created: bool, request):
        if is_created:
            data["created_at"] = datetime.now(timezone.utc)
