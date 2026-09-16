from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class YandexToken(Base):
    __tablename__ = "yandex_tokens"
    id: Mapped[str] = mapped_column(String, primary_key=True, default="main")
    access_token: Mapped[str] = mapped_column(String)
    refresh_token: Mapped[str] = mapped_column(String)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
