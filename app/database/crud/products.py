from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.database import Product, ProductStep, SessionDep, StepDefinition, Process
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models.product_step import StepStatus
from app.database.schemas.product import ProductCreate


def get_product_repo(session: SessionDep) -> "ProductRepository":
    return ProductRepository(session)


class ProductRepository(GetBackNextIdMixin[Product]):
    model = Product

    async def create_product(self, product_in: ProductCreate) -> Product:
        # 1) создаём продукт
        product = product_in.to_orm()
        self.session.add(product)

        # получаем product.id, но ещё не коммитим
        await self.session.flush()

        # 2) подтягиваем процесс с шагами (явно)
        process = await self.session.get(
            Process,
            product_in.process_id,
            options=[selectinload(Process.steps)],
        )
        if process is None:
            raise ValueError("Процесс с таким process_id не найден")

        # 3) создаём шаги продукта
        for step_def in process.steps:
            self.session.add(
                ProductStep(
                    product_id=product.id,
                    step_definition_id=step_def.id,
                    status=StepStatus.pending,
                )
            )

        # 4) коммитим транзакцию
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # 5) перечитываем продукт с нужными relation
        await self.session.refresh(product)
        created = await self.get(id=product.id)
        return created

    async def get(
        self,
        *,
        id: Optional[int] = None,
        serial_number: Optional[str] = None,
    ) -> Product:
        if id is None and serial_number is None:
            raise ValueError("Нужно указать id или serial_number")
        if id is not None and serial_number is not None:
            raise ValueError("Укажи только одно из: id или serial_number")

        stmt = select(self.model).options(
            joinedload(self.model.process),
            joinedload(self.model.steps)
            .joinedload(ProductStep.step_definition)
            .joinedload(StepDefinition.template),
            joinedload(self.model.steps).joinedload(ProductStep.performed_by),
        )

        if id is not None:
            stmt = stmt.where(self.model.id == id)
        else:
            stmt = stmt.where(self.model.serial_number == serial_number)

        product = await self.session.scalar(stmt)

        if product is not None:
            return product

        ident = id if id is not None else serial_number
        raise HTTPException(
            status_code=404,
            detail=f"Продукт с идентификатором {ident} не найден",
        )
