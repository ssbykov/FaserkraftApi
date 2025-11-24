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
        # 1️⃣ создаём продукт
        product = product_in.to_orm()
        self.session.add(product)

        # получаем product.id, но ещё не коммитим
        await self.session.flush()

        # 2️⃣ подтягиваем процесс с шагами
        process = await self.session.get(
            Process,
            product_in.process_id,
            options=[selectinload(Process.steps)],
        )
        if process is None:
            # Можно кинуть ValueError, её перехватит эндпоинт
            raise ValueError("Процесс с таким process_id не найден")

        # 3️⃣ создаём шаги продукта
        for step_def in process.steps:
            self.session.add(
                ProductStep(
                    product_id=product.id,
                    step_definition_id=step_def.id,
                    status=StepStatus.pending,
                )
            )

        # 4️⃣ коммитим транзакцию
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # 5️⃣ при необходимости обновляем объект
        await self.session.refresh(product)
        return product

    async def get(self, serial_number: str) -> Product:
        stmt = (
            select(self.model)
            .options(
                joinedload(self.model.steps)
                .joinedload(ProductStep.step_definition)
                .joinedload(StepDefinition.template)
            )
            .where(self.model.serial_number == serial_number)
        )
        product = await self.session.scalar(stmt)
        if product is not None:
            return product

        raise HTTPException(
            status_code=404,
            detail=f"Продукт с серийным номером {serial_number} не найден",
        )
