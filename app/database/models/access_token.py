from typing import TYPE_CHECKING

from fastapi_users_db_sqlalchemy.access_token import (
    SQLAlchemyAccessTokenDatabase,
    SQLAlchemyBaseAccessTokenTable,
)
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AccessToken(Base, SQLAlchemyBaseAccessTokenTable[int]):
    """
    Модель токена доступа для аутентификации пользователей.
    
    Наследуется от Base и SQLAlchemyBaseAccessTokenTable для работы с токенами
    доступа в системе FastAPI Users. Содержит связь с пользователем через
    внешний ключ и предоставляет методы для работы с базой данных токенов.
    
    Attributes:
        user_id (int): Идентификатор пользователя, которому принадлежит токен.
                      Связан с таблицей users через внешний ключ с каскадным удалением.
    """
    __tablename__ = "access_tokens"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="cascade"), nullable=False
    )  # type: ignore

    @classmethod
    def get_db(cls, session: "AsyncSession"):  # type: ignore
        return SQLAlchemyAccessTokenDatabase(session, cls)
