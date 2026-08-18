import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import ProductStep, StepDefinition, SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models.product import ProductStatus, Product
from app.database.models.product_step import StepStatus
from app.database import Process

logger = logging.getLogger(__name__)


def get_products_steps_repo(session: SessionDep) -> "ProductStepRepository":
    return ProductStepRepository(session)


class ProductStepRepository(GetBackNextIdMixin[ProductStep]):
    model = ProductStep

    async def accept_step(
        self,
        step_id: int,
        employee_id: int,
    ) -> type[ProductStep] | None:
        step = await self.session.get(self.model, step_id)
        if not step:
            return None

        step_def = await self.session.get(StepDefinition, step.step_definition_id)

        prev_step = (
            await self.session.execute(
                select(ProductStep)
                .join(StepDefinition)
                .where(
                    ProductStep.product_id == step.product_id,
                    StepDefinition.process_id == step_def.process_id,
                    StepDefinition.order == step_def.order - 1,
                )
            )
        ).scalar_one_or_none()

        if prev_step and prev_step.status != StepStatus.done:
            raise ValueError("Нельзя принять этот этап, пока предыдущий не завершён.")

        step.status = StepStatus.done
        step.performed_by_id = employee_id
        step.performed_at = datetime.now(ZoneInfo("Europe/Moscow"))

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(step)
        return step

    async def change_performer_if_done(
        self,
        step_id: int,
        employee_id: int,
    ) -> type[ProductStep] | None:
        step = await self.session.get(self.model, step_id)
        if not step:
            return None

        if step.status != StepStatus.done:
            raise ValueError("Нельзя сменить исполнителя, этап ещё не закрыт.")

        step.performed_by_id = employee_id

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(step)
        return step

    async def reset_step_and_subsequent(self, step_id: int) -> Product | None:
        step = await self.session.get(self.model, step_id)
        if not step:
            return None

        # Проверка 1: этап должен быть уже выполнен
        if step.status != StepStatus.done:
            raise ValueError("Нельзя сбросить этап: этап ещё не выполнен.")

        # Получаем базовый продукт для проверки бизнес-правил
        product = await self.session.get(Product, step.product_id)
        if not product:
            return None

        # Проверка 2: упаковка
        if product.packaging_id is not None:
            raise ValueError("Нельзя сбросить этапы: продукт уже упакован.")

        # Проверка 3: статус продукта
        if product.status != ProductStatus.normal:
            raise ValueError(
                f"Нельзя сбросить этапы: статус продукта '{product.status}', ожидался 'normal'."
            )

        step_def = await self.session.get(StepDefinition, step.step_definition_id)
        if not step_def:
            return None

        # Находим текущий и последующие этапы процесса
        query = (
            select(ProductStep)
            .join(StepDefinition)
            .where(
                ProductStep.product_id == step.product_id,
                StepDefinition.process_id == step_def.process_id,
                StepDefinition.order >= step_def.order,
            )
        )
        steps_to_reset = (await self.session.execute(query)).scalars().all()

        for s in steps_to_reset:
            s.status = StepStatus.pending
            s.accepted_by_id = None
            s.accepted_at = None
            s.performed_by_id = None
            s.performed_at = None

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # Явно загружаем продукт со всеми необходимыми связями для Pydantic схемы (ProductRead)
        query_full_product = (
            select(Product)
            .options(
                selectinload(Product.steps).selectinload(ProductStep.step_definition),
                selectinload(Product.steps).selectinload(ProductStep.performed_by),
                selectinload(Product.packaging),
                selectinload(Product.work_process).selectinload(Process.steps),
            )
            .where(Product.id == product.id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(query_full_product)).scalar_one_or_none()