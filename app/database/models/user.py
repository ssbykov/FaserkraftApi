from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseWithId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class User(BaseWithId, SQLAlchemyBaseUserTable[int]):  # type: ignore[misc]
    """
    Модель пользователя для аутентификации и управления доступом.

    Наследуется от `BaseWithId` и `SQLAlchemyBaseUserTable`, предоставляя базовую
    функциональность для работы с пользователями в FastAPI Users.

    Атрибуты:
        id: Уникальный идентификатор пользователя (наследуется от BaseWithId).
        email: Электронная почта пользователя. Обязательное поле.
        is_active: Флаг активности пользователя.
        is_superuser: Флаг суперпользователя.
        is_verified: Флаг подтверждения электронной почты.
        created_at: Дата и время создания пользователя.
        updated_at: Дата и время последнего обновления информации о пользователе.

    Методы:
        get_db: Возвращает объект SQLAlchemyUserDatabase для взаимодействия с БД.
        __str__: Возвращает email пользователя как строковое представление.
        model_dump: Возвращает словарь с основными полями пользователя.
    """
    __tablename__ = "users"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        default=func.now(),
        server_default=func.now(),
    )

    @classmethod
    def get_db(cls, session: "AsyncSession"):  # type: ignore
        return SQLAlchemyUserDatabase(session, cls)

    def __str__(self) -> str:
        return self.email

    def model_dump(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "is_verified": self.is_verified,
        }
