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

    column_labels = {
        "deviceId": "ID устройства",
        "model": "Модель",
        "manufacturer": "Производитель",
        "is_active": "Активно",
    }
    can_export = False
