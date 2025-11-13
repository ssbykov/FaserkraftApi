from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.database import Product, ProductStep, SessionDep, StepDefinition
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.crud.processes import ProcessRepository
from app.database.models.product_step import StepStatus
from app.database.schemas.product import ProductCreate


def get_product_repo(session: SessionDep) -> "ProductRepository":
    return ProductRepository(session)


class ProductRepository(GetBackNextIdMixin[Product]):
    session: AsyncSession
    model = Product

    async def create_product(self, product_in: ProductCreate):
        # 1️⃣ Create product

        product = product_in.to_orm()
        self.session.add(product)
        await self.session.flush()
        product_id = product.id

        # 2️⃣ Create all steps for this product
        repo = ProcessRepository(self.session)
        process = await repo.get(product_in.process_id)
        for step_def in process.steps:
            ps = ProductStep(
                product_id=product_id,
                step_definition_id=step_def.id,
                status=StepStatus.pending,
            )
            self.session.add(ps)

        await self.session.commit()
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
        if product:
            return product
        raise HTTPException(
            status_code=404, detail=f"Продукт с id {serial_number} не найден"
        )
