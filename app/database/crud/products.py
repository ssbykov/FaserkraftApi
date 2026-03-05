from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.orm import joinedload, selectinload, aliased

from app.database import (
    Product,
    ProductStep,
    SessionDep,
    StepDefinition,
    Process,
    StepTemplate,
)
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

    async def set_status(self, product_id: int, status: ProductStatus) -> Product:
        product = await self.get(id=product_id)

        if product.status == status:
            return product

        product.status = status

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(product)
        return product

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

    async def get_counts_by_last_done_step(self):

        ps_alias = aliased(ProductStep)
        sd_alias = aliased(StepDefinition)

        subq = (
            select(
                ps_alias.product_id,
                ps_alias.step_definition_id,
                func.row_number()
                .over(
                    partition_by=ps_alias.product_id,
                    order_by=(
                        desc(sd_alias.order),
                        desc(ps_alias.accepted_at),
                    ),
                )
                .label("rn"),
            )
            .join(sd_alias, sd_alias.id == ps_alias.step_definition_id)
            .where(ps_alias.status == StepStatus.done)
            .subquery()
        )

        # Основной запрос
        stmt = (
            select(
                Product.process_id,
                Process.name.label(
                    "process_name"
                ),  # предполагается поле name у Process
                subq.c.step_definition_id,
                StepTemplate.name.label("step_name"),  # берем имя из StepTemplate
                func.count(Product.id).label("count"),
            )
            .join(subq, subq.c.product_id == Product.id)
            .join(StepDefinition, StepDefinition.id == subq.c.step_definition_id)
            .join(
                StepTemplate, StepTemplate.id == StepDefinition.template_id
            )  # присоединяем StepTemplate
            .join(Process, Process.id == Product.process_id)
            .where(Product.status == ProductStatus.normal, Product.packaging_id is None)
            .where(subq.c.rn == 1)
            .group_by(
                Product.process_id,
                Process.name,
                subq.c.step_definition_id,
                StepTemplate.name,
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()
        return [dict(row._mapping) for row in rows]

    async def get_finished_products(self) -> list[Product]:
        """
        Продукты со статусом normal, у которых все шаги завершены (StepStatus.done).
        """

        # подзапрос: есть ли у продукта хотя бы один НЕ завершённый шаг
        not_done_exists = (
            select(ProductStep.id)
            .where(
                ProductStep.product_id == Product.id,
                ProductStep.status != StepStatus.done,
            )
            .exists()
        )

        stmt = (
            select(Product)
            .where(Product.status == ProductStatus.normal)
            .where(~not_done_exists)  # NOT EXISTS not-done шага
            .options(
                selectinload(Product.work_process),
            )
        )

        result = await self.session.execute(stmt)

        return list(result.scalars().all())