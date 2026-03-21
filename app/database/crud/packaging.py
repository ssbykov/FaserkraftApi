from datetime import datetime, timezone
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.database import SessionDep, Product
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import Packaging
from app.database.schemas.packaging import PackagingCreate


def get_packaging_repo(session: SessionDep) -> "PackagingRepository":
    return PackagingRepository(session)

class PackagingRepository(GetBackNextIdMixin[Packaging]):
    model = Packaging

    async def create_packaging(
            self,
            packaging_in: PackagingCreate,
            *,
            products: List[int],
    ) -> Packaging:
        # ищем существующую упаковку по serial_number
        stmt = select(Packaging).where(
            Packaging.serial_number == packaging_in.serial_number
        )
        res = await self.session.execute(stmt)
        packaging = res.scalar_one_or_none()

        now_utc = datetime.now(timezone.utc)

        if packaging is None:
            # создаём новую упаковку
            packaging = packaging_in.to_orm()
            packaging.performed_at = now_utc
        else:
            # обновляем только эти поля
            packaging.performed_at = now_utc
            packaging.performed_by_id = packaging_in.performed_by.id

        self.session.add(packaging)

        try:
            # получаем id для новой упаковки
            await self.session.flush()
            await self.session.refresh(packaging)

            # синхронизируем продукты
            new_ids = set(products)

            # текущие продукты этой упаковки
            stmt_current = select(Product.id).where(
                Product.packaging_id == packaging.id
            )
            res_current = await self.session.execute(stmt_current)
            current_ids = set(res_current.scalars().all())

            to_attach = new_ids - current_ids
            to_detach = current_ids - new_ids

            if to_attach:
                stmt_attach = (
                    update(Product)
                    .where(Product.id.in_(to_attach))
                    .values(packaging_id=packaging.id)
                )
                await self.session.execute(stmt_attach)

            if to_detach:
                stmt_detach = (
                    update(Product)
                    .where(Product.id.in_(to_detach))
                    .values(packaging_id=None)  # или другое “отвязочное” значение
                )
                await self.session.execute(stmt_detach)

            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(packaging)
        return packaging

    async def get(
        self,
        *,
        id: Optional[int] = None,
        serial_number: Optional[str] = None,
    ) -> Packaging:
        if id is None and serial_number is None:
            raise ValueError("Нужно указать id или serial_number")
        if id is not None and serial_number is not None:
            raise ValueError("Укажи только одно из: id или serial_number")

        stmt = select(self.model).options(
            joinedload(self.model.products),  # если надо подтянуть продукты
        )

        if id is not None:
            stmt = stmt.where(self.model.id == id)
        else:
            stmt = stmt.where(self.model.serial_number == serial_number)

        packaging = await self.session.scalar(stmt)

        if packaging is not None:
            return packaging

        ident = id if id is not None else serial_number
        raise HTTPException(
            status_code=404,
            detail=f"Упаковка с идентификатором {ident} не найдена",
        )