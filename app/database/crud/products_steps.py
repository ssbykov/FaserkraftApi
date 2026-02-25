from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Mapped

from app.database import ProductStep, StepDefinition, SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models.product_step import StepStatus


def get_products_steps_repo(session: SessionDep) -> "ProductStepRepository":
    return ProductStepRepository(session)


class ProductStepRepository(GetBackNextIdMixin[ProductStep]):
    model = ProductStep

    async def accept_step(self, step_id: int, employee_id: Mapped[int]):
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
