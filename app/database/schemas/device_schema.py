from app.database import BaseSchema


class DeviceCreate(BaseSchema):
    deviceId: str
    model: str
    manufacturer: str
    androidVersion: str
