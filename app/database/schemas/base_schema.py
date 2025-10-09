from typing import Type

from pydantic import BaseModel, Field

from app.database import BaseWithId


class BaseSchema(BaseModel):
    """
    Базовый класс для схем, которые могут быть преобразованы в ORM-модели.
    """

    base_class: Type[BaseWithId] = Field(default=BaseWithId, exclude=True)

    def to_orm(self) -> BaseWithId:
        """
        Преобразует схему в ORM-модель.
        """
        column_names = list(self.base_class.__table__.columns.keys())
        column_names.remove("id")
        if sorted(column_names) == sorted(list(self.model_dump().keys())):
            return self.base_class(**self.model_dump())
        raise ValueError(
            "Параметры model_class не соответствуют параметрам базового класса."
        )
