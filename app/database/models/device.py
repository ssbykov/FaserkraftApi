from zoneinfo import ZoneInfo

from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from .base import BaseWithId


class Device(BaseWithId):
    __tablename__ = "devices"

    device_id = Column(String, unique=True, nullable=False)
    model = Column(String, nullable=False)
    manufacturer = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="device", uselist=False)

    def __repr__(self):
        created_at = self.created_at.astimezone(ZoneInfo("Europe/Moscow")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return f"id: {self.id}, модель: {self.model}, регистрация: {created_at}"
