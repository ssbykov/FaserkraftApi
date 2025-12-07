from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime

from .base import Base


class YandexToken(Base):
    __tablename__ = "yandex_tokens"
    id = Column(String, primary_key=True, default="main")
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
