from datetime import datetime
from typing import ClassVar, Type
from zoneinfo import ZoneInfo

from app.database import BaseSchema
from app.database.models import Device


class DeviceBase(BaseSchema):
    device_id: str
    model: str
    manufacturer: str


class DeviceCreate(DeviceBase):
    is_active: bool = True
    created_at: datetime = datetime.now(ZoneInfo("Europe/Moscow"))
    base_class: ClassVar[Type[Device]] = Device


class DeviceRead(DeviceBase):
    id: int

    model_config = {"from_attributes": True}


class DeviceRegister(DeviceCreate):
    token: str
    password: str
    user_id: int


class DeviceResponse(DeviceBase):
    user_email: str
    employee_name: str
