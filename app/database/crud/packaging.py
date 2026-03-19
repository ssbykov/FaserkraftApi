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
            # создаём новую упаковку из входной схемы
            packaging = packaging_in.to_orm()
            packaging.performed_at = now_utc
        else:
            # если упаковка есть — меняем только executed‑поля
            packaging.performed_at = now_utc
            packaging.performed_by_id = packaging_in.performed_by_id

        self.session.add(packaging)

        try:
            # получаем id (для новой упаковки)
            await self.session.flush()
            await self.session.refresh(packaging)

            # products всегда “перепривязываем” к этой упаковке
            if products:
                stmt = (
                    update(Product)
                    .where(Product.id.in_(products))
                    .values(packaging_id=packaging.id)
                )
                await self.session.execute(stmt)

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