from sqlalchemy import Column, String, Boolean

from .base import BaseWithId


class Device(BaseWithId):
    __tablename__ = "devices"

    deviceId = Column(String, unique=True, nullable=False)
    model = Column(String, nullable=False)
    manufacturer = Column(String, nullable=False)
    androidVersion = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)

    def __repr__(self):
        return self.deviceId
