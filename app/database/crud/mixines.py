from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import (
    Any,
    Optional,
    Type,
    Sequence,
    Generic,
    List,
)

from sqlalchemy import select, Select, String, func, Integer, Boolean, Date, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.type_vars import T


class GetBackNextIdMixin(ABC, Generic[T]):
    session: AsyncSession

    @property
    @abstractmethod
    def model(self) -> Type[T]:
        pass

    def __init__(self, session: AsyncSession):
        self.session = session
        self.main_stmt = select(self.model)

    async def get_adjacent_id(
            self,
            current_val: int | str,
            list_query: Select[Any],
            sort_column: str = "id",
            is_next: bool = True,
    ) -> Optional[int]:
        # 1. Убираем существующую сортировку из list_query и делаем из него подзапрос
        subq = list_query.order_by(None).subquery()

        # 2. Достаем колонки уже из подзапроса, а не из self.model
        sort_col = subq.c[sort_column]
        id_col = subq.c["id"]

        # 3. Приводим входящее значение к нужному типу
        typed_val = convert_to_column_type(current_val, sort_col.type)

        # 4. Формируем условия и направление сортировки
        if is_next:
            condition = sort_col > typed_val
            order_by = sort_col.asc()
        else:
            condition = sort_col < typed_val
            order_by = sort_col.desc()

        # 5. Строим новый чистый запрос к нашему подзапросу
        stmt = (
            select(id_col)
            .select_from(subq)
            .where(condition)
            .order_by(order_by)
            .limit(1)
        )

        return await self.session.scalar(stmt)

    async def get_all(self) -> Sequence[T]:
        result = await self.session.execute(self.main_stmt)
        obj_list = result.scalars().all()
        return obj_list

    async def get_count_items(self, conditions: Optional[List[bool]] = None) -> int:
        query = select(func.count(self.model.id))
        if conditions:
            query = query.where(*conditions)  # применяем условия, если они есть
        result = await self.session.execute(query)
        return result.scalar_one_or_none() or 0

    async def get_async_position(
            self,
            target_val: int,
            column: str,
            request: Request,
            is_desc: bool = False,
    ) -> int | None:
        sort_column = getattr(self.model, column)
        column_type = sort_column.type
        conditions = []
        user = request.session.get("user")
        if hasattr(self.model, "user_id") and user and not user.get("is_superuser"):
            conditions.append(getattr(self.model, "user_id") == user.get("id"))

        order_by = sort_column.desc() if is_desc else sort_column.asc()
        subquery = (
            (
                select(
                    sort_column,
                    func.row_number().over(order_by=order_by).label("row_num"),
                )
            )
            .where(*conditions)
            .subquery()
        )

        query = select(subquery.c.row_num).where(
            subquery.c[column]
            == convert_to_column_type(target_val, column_type)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, obj_id: int) -> T | None:
        query = self.main_stmt.where(self.model.id == obj_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


def convert_to_column_type(variable: Any, column_type: Any) -> Any:
    if isinstance(column_type, Integer):
        return int(variable)
    elif isinstance(column_type, String):
        return str(variable)
    elif isinstance(column_type, Boolean):
        return bool(variable)
    elif isinstance(column_type, Date) or isinstance(column_type, DateTime):
        dt = datetime.strptime(str(variable).split("T")[0], "%Y-%m-%d")
        if isinstance(column_type, Date):
            return dt.date()
        return dt
    else:
        raise ValueError(f"Unsupported column type: {type(column_type)}")