from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from app.core import settings


class Base(DeclarativeBase):
    """
    Базовый абстрактный класс для всех моделей SQLAlchemy.

    Использует настройки метаданных из `settings.db.naming_convention` для единообразия именования объектов в базе данных.
    Наследуется от `DeclarativeBase`, что позволяет использовать декларативный стиль определения моделей SQLAlchemy.
    """

    __abstract__ = True

    metadata = MetaData(naming_convention=settings.db.naming_convention)


class BaseWithId(Base):
    """
    Базовый класс для моделей, содержащих поле `id`.

    Атрибуты:
        id: Первичный ключ модели. Целое число, уникальное и индексированное.
        init_data: Список словарей с начальными данными для заполнения таблицы при инициализации (опционально).
    """

    __abstract__ = True

    init_data: list[dict[str, Any]] = []
    id: Mapped[int] = mapped_column(primary_key=True, index=True, unique=True)
