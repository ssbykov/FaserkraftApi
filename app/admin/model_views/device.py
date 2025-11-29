from app.admin.custom_model_view import CustomModelView
from app.database.crud.devices import DeviceRepository
from app.database.models import Device


class DeviceAdmin(
    CustomModelView[Device],
    model=Device,
):
    repo_type = DeviceRepository
    name_plural = "Устройства"
    name = "Устройство"
    category = "Пользователи"

    column_list = (
        "model",
        "employee",
        "is_active",
    )

    column_labels = {
        "device_id": "ID устройства",
        "model": "Модель",
        "manufacturer": "Производитель",
        "is_active": "Активно",
    }

    form_rules = [
        "is_active",
        "employee",
    ]

    can_export = False
    can_create = False
