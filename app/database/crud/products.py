from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.database import Product, ProductStep, SessionDep, StepDefinition, Process
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models.product import ProductStatus
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

        # 2) подтягиваем процесс с шагами (используем select)
        stmt = (
            select(Process)
            .where(Process.id == product_in.process_id)
            .options(selectinload(Process.steps))
        )

        result = await self.session.execute(stmt)
        process = result.scalar_one_or_none()

        if process is None:
            await self.session.rollback()
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
            joinedload(self.model.work_process),
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

    async def _set_status(self, product_id: int, status: ProductStatus) -> Product:
        product = await self.get(id=product_id)

        if product.status == status:
            return product

        product.status = status
        await self.session.flush()
        return product

    async def send_to_scrap(self, product_id: int) -> Product:
        return await self._set_status(product_id, ProductStatus.scrap)

    async def send_to_rework(self, product_id: int) -> Product:
        return await self._set_status(product_id, ProductStatus.rework)

    async def restore(self, product_id: int) -> Product:
        return await self._set_status(product_id, ProductStatus.normal)

    async def change_product_process(
        self,
        product_id: int,
        new_process_id: int,
    ) -> Product:
        # 1) грузим продукт с шагами и их StepDefinition + StepTemplate
        stmt_product = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.steps)
                .selectinload(ProductStep.step_definition)
                .selectinload(StepDefinition.template),
                selectinload(Product.work_process),
            )
        )
        result_product = await self.session.execute(stmt_product)
        product: Product | None = result_product.scalar_one_or_none()

        if product is None:
            raise ValueError("Продукт не найден")

        # 2) грузим новый процесс с его StepDefinition (+ template)
        stmt_process = (
            select(Process)
            .where(Process.id == new_process_id)
            .options(selectinload(Process.steps).selectinload(StepDefinition.template))
        )
        result_process = await self.session.execute(stmt_process)
        new_process: Process | None = result_process.scalar_one_or_none()

        if new_process is None:
            raise ValueError("Процесс с таким new_process_id не найден")

        # 3) индекс: template_id -> список ProductStep (на случай повторов)
        steps_by_template: dict[int, list[ProductStep]] = {}
        for ps in product.steps:
            tid = ps.step_definition.template_id
            steps_by_template.setdefault(tid, []).append(ps)

        # 4) строим новый список шагов продукта
        new_product_steps: list[ProductStep] = []

        # сортируем шаги процесса по order (у тебя это уже в relationship(order_by),
        # но тут делаем явно, чтобы не зависеть от настроек Product.steps) [web:21]
        new_defs_sorted = sorted(new_process.steps, key=lambda sd: sd.order)

        used_old_steps: set[int] = set()

        for step_def in new_defs_sorted:
            tid = step_def.template_id
            candidates = steps_by_template.get(tid) or []

            # ищем первый неиспользованный ProductStep с этим template_id
            old_step = None
            for c in candidates:
                if c.id not in used_old_steps:
                    old_step = c
                    break

            if old_step is not None:
                # переиспользуем существующий шаг: меняем только step_definition_id
                old_step.step_definition_id = step_def.id
                used_old_steps.add(old_step.id)
                new_product_steps.append(old_step)
            else:
                # нет старого шага с таким шаблоном — создаём новый
                new_product_steps.append(
                    ProductStep(
                        product_id=product.id,
                        step_definition_id=step_def.id,
                        status=StepStatus.pending,
                    )
                )

        # 5) лишние старые шаги (у которых шаблон не встречается в новом процессе
        # или их больше, чем нужно) не попадают в product.steps[:] и станут orphan,
        # если на relationship(Product.steps) есть delete-orphan [web:23][web:28]
        product.steps[:] = new_product_steps  # корректная замена коллекции [web:15]

        # 6) меняем процесс у продукта
        product.process_id = new_process_id

        # 7) коммит
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(product)
        return product
