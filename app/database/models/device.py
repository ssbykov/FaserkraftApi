from datetime import datetime
from typing import TYPE_CHECKING, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseWithId

if TYPE_CHECKING:
    from .employee import Employee


class Device(BaseWithId):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String, unique=True)
    model: Mapped[str] = mapped_column(String)
    manufacturer: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    employee: Mapped[Optional["Employee"]] = relationship(
        back_populates="device", uselist=False
    )

    def __repr__(self) -> str:
        created_at = self.created_at.astimezone(ZoneInfo("Europe/Moscow")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return f"id: {self.id}, модель: {self.model}, регистрация: {created_at}"