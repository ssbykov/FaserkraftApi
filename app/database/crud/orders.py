from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette import status

from app.database import SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import Order, OrderItem
from app.database.schemas.order import OrderCreate, OrderItemCreate, OrderUpdate
from database.schemas.order import OrderClose


def get_order_repo(session: SessionDep) -> "OrderRepository":
    return OrderRepository(session)


class OrderRepository(GetBackNextIdMixin[Order]):
    model = Order

    async def _get_order_with_relations(self, order_id: int) -> Any | None:
        """Перезапрашивает заказ со всеми необходимыми для OrderRead связями"""
        stmt_ret = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.work_process),
                selectinload(Order.packaging),
            )
            .where(Order.id == order_id)
        )
        return await self.session.scalar(stmt_ret)

    # === 1. ОБНОВЛЕНИЕ ОСНОВНЫХ ДАННЫХ ЗАКАЗА ===
    async def update(
        self,
        order_in: OrderUpdate,
    ) -> Any | None:

        order_id = order_in.id
        stmt = select(Order).where(Order.id == order_id)
        order = await self.session.scalar(stmt)

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с идентификатором {order_id} не найден",
            )

        # Обновляем только основные поля
        order.contract_number = order_in.contract_number
        order.contract_date = order_in.contract_date
        order.planned_shipment_date = order_in.planned_shipment_date

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self._get_order_with_relations(order.id)

    # === 2. ОБНОВЛЕНИЕ ТОЛЬКО СОСТАВА ЗАКАЗА (ITEMS) ===
    async def update_items(
        self,
        order_id: int,
        items_in: list[OrderItemCreate],
    ) -> Any | None:

        # Обязательно подгружаем items, чтобы SQLAlchemy понял,
        # какие старые записи нужно удалить (delete-orphan)
        stmt = (
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
        order = await self.session.scalar(stmt)

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с идентификатором {order_id} не найден",
            )

        # Перезаписываем позиции. Старые отсутствующие автоматически удалятся.
        order.items = [
            OrderItem(process_id=item.process_id, quantity=item.quantity)
            for item in items_in
        ]

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self._get_order_with_relations(order.id)

    # === 3. СОЗДАНИЕ ЗАКАЗА (ДЛЯ ПОЛНОТЫ КАРТИНЫ) ===
    async def create(
        self,
        order_in: OrderCreate,
    ) -> Any | None:

        order = Order(
            contract_number=order_in.contract_number,
            contract_date=order_in.contract_date,
            planned_shipment_date=order_in.planned_shipment_date,
        )

        self.session.add(order)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self._get_order_with_relations(order.id)

    # === 4. ЗАКРЫТИЕ ЗАКАЗА (ОТГРУЗКА) ===
    async def close(
        self,
        order_id: int,
        close_in: OrderClose,
    ) -> Any | None:

        stmt = select(Order).where(Order.id == order_id)
        order = await self.session.scalar(stmt)

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с идентификатором {order_id} не найден",
            )

        if order.shipment_date is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Заказ {order_id} уже отгружен",
            )

        # Обновляем данные об отгрузке
        order.shipment_date = close_in.shipment_date
        order.shipment_by_id = close_in.shipment_by_id

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self._get_order_with_relations(order.id)

    async def delete(
        self,
        *,
        id: int,
    ) -> None:

        stmt = select(self.model).where(self.model.id == id)
        order = await self.session.scalar(stmt)

        if order is None:
            raise HTTPException(
                status_code=404,
                detail=f"Заказ с идентификатором {id} не найден",
            )

        await self.session.delete(order)
        await self.session.commit()
