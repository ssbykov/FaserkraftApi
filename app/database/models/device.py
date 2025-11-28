from sqlalchemy import Column, String, Boolean, DateTime, func

from .base import BaseWithId


class Device(BaseWithId):
    __tablename__ = "devices"

    device_id = Column(String, unique=True, nullable=False)
    model = Column(String, nullable=False)
    manufacturer = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return self.device_id
