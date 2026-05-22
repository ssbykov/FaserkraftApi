from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseWithId


class BackupDb(BaseWithId):
    """
    Модель для представления резервной копии в базе данных.

    Атрибуты:
        id: Уникальный идентификатор резервной копии (наследуется от BaseWithId).
        name: Имя резервной копии. Максимальная длина - 50 символов. Обязательное поле.
    """

    __tablename__ = "backups"
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    def __str__(self) -> str:
        return self.name
