from datetime import date as date_type
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from starlette import status

PRODUCTION_TIMEZONE = ZoneInfo("Europe/Moscow")

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
    DailyPlan,
)
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import DailyPlanStep
from app.database.models.product import ProductStatus
from app.database.models.product_step import StepStatus
from app.database.schemas.product import ProductCreate
from database import Employee
from database.models import SizeType


def get_product_repo(session: SessionDep) -> "ProductRepository":
    return ProductRepository(session)


def _make_datetime_period(
    date_from: date_type,
    date_to: date_type,
) -> tuple[datetime, datetime]:
    """
    Преобразует календарный диапазон в полуоткрытый интервал datetime:
    [date_from 00:00:00; date_to + 1 день 00:00:00).

    Все даты трактуются в производственной timezone.
    """
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from не может быть позже date_to",
        )

    period_start = datetime.combine(
        date_from,
        time.min,
        tzinfo=PRODUCTION_TIMEZONE,
    )
    period_end = datetime.combine(
        date_to + timedelta(days=1),
        time.min,
        tzinfo=PRODUCTION_TIMEZONE,
    )

    return period_start, period_end


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

        if product.packaging_id:
            raise HTTPException(
                status_code=409, detail="Запрещено менять тип упакованного продукта"
            )

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
                StepTemplate.name.label("step_name"),
                StepTemplate.name_genitive.label("step_name_genitive"),
                func.count(Product.id).label("count"),
            )
            .join(subq, subq.c.product_id == Product.id)
            .join(StepDefinition, StepDefinition.id == subq.c.step_definition_id)
            .join(
                StepTemplate, StepTemplate.id == StepDefinition.template_id
            )  # присоединяем StepTemplate
            .join(Process, Process.id == Product.process_id)
            .where(Product.status == ProductStatus.normal)
            .where(Product.packaging_id.is_(None))
            .where(subq.c.rn == 1)
            .group_by(
                Product.process_id,
                Process.name,
                subq.c.step_definition_id,
                StepTemplate.name,
                StepTemplate.name_genitive,
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()
        return [dict(row._mapping) for row in rows]

    async def get_finished_products(
        self,
        *,
        employee_id: int | None = None,
    ) -> list[Product]:
        today = date_type.today()

        not_done_exists = (
            select(ProductStep.id)
            .where(
                ProductStep.product_id == Product.id,
                ProductStep.status != StepStatus.done,
            )
            .exists()
        )

        # базовые условия «завершённого» продукта
        conditions = [
            Product.status == ProductStatus.normal,
            Product.packaging_id.is_(None),
            ~not_done_exists,
        ]

        if employee_id is not None:
            # последний выполненный шаг продукта (по порядку StepDefinition.order)
            last_step_step_def_id_subq = (
                select(ProductStep.step_definition_id)
                .join(
                    StepDefinition, StepDefinition.id == ProductStep.step_definition_id
                )
                .where(
                    ProductStep.product_id == Product.id,
                    ProductStep.status == StepStatus.done,
                )
                .order_by(StepDefinition.order.desc())
                .limit(1)
                .scalar_subquery()
            )

            # множество step_definition_id из дневного плана сотрудника на сегодня
            plan_step_def_ids_subq = (
                select(DailyPlanStep.step_definition_id)
                .join(DailyPlan, DailyPlanStep.daily_plan_id == DailyPlan.id)
                .where(
                    DailyPlan.date == today,
                    DailyPlan.employee_id == employee_id,
                )
            )

            # пересечение: последний шаг продукта должен быть в плане
            conditions.append(last_step_step_def_id_subq.in_(plan_step_def_ids_subq))

        stmt = (
            select(Product)
            .where(*conditions)
            .options(selectinload(Product.work_process))
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_finished_products_stats_by_period(
        self,
        date_from: date_type,
        date_to: date_type,
    ) -> list[dict]:
        """
        Считает количество завершённых продуктов по процессам, у которых
        последний технологический этап был выполнен в указанном периоде.

        Период интерпретируется в производственной timezone Europe/Moscow:
        [date_from 00:00:00; date_to + 1 день 00:00:00).
        """
        period_start, period_end = _make_datetime_period(date_from, date_to)

        not_done_exists = (
            select(ProductStep.id)
            .where(
                ProductStep.product_id == Product.id,
                ProductStep.status != StepStatus.done,
            )
            .exists()
        )

        last_step_performed_at_subq = (
            select(ProductStep.performed_at)
            .join(
                StepDefinition,
                StepDefinition.id == ProductStep.step_definition_id,
            )
            .where(
                ProductStep.product_id == Product.id,
                ProductStep.status == StepStatus.done,
                ProductStep.performed_at.is_not(None),
            )
            .order_by(
                StepDefinition.order.desc(),
                ProductStep.performed_at.desc(),
                ProductStep.id.desc(),
            )
            .limit(1)
            .correlate(Product)
            .scalar_subquery()
        )

        stmt = (
            select(
                Process.id.label("process_id"),
                Process.name.label("process_name"),
                func.count(Product.id).label("count"),
            )
            .select_from(Product)
            .join(Process, Process.id == Product.process_id)
            .where(
                Product.status == ProductStatus.normal,
                Product.packaging_id.is_(None),
                ~not_done_exists,
                last_step_performed_at_subq >= period_start,
                last_step_performed_at_subq < period_end,
            )
            .group_by(Process.id, Process.name)
        )

        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def get_completed_steps_stats_by_period(
        self,
        date_from: date_type,
        date_to: date_type,
        employee_id: int | None = None,
    ) -> list[dict]:
        """
        Возвращает агрегированную статистику выполненных этапов за период
        по процессу, типоразмеру, этапу и сотруднику.

        Период задаётся в московском производственном времени и имеет вид:
        [date_from 00:00; date_to + 1 день 00:00).
        """
        period_start, period_end = _make_datetime_period(date_from, date_to)

        stmt = (
            select(
                Product.process_id,
                Process.name.label("process_name"),
                Process.size_type_id,
                SizeType.name.label("size_type_name"),
                ProductStep.step_definition_id,
                StepDefinition.order.label("order"),
                StepTemplate.name.label("step_name"),
                ProductStep.performed_by_id.label("employee_id"),
                Employee.name.label("employee_name"),
                func.count(ProductStep.id).label("count"),
            )
            .select_from(ProductStep)
            .join(Product, Product.id == ProductStep.product_id)
            .join(Process, Process.id == Product.process_id)
            .outerjoin(SizeType, SizeType.id == Process.size_type_id)
            .join(StepDefinition, StepDefinition.id == ProductStep.step_definition_id)
            .join(StepTemplate, StepTemplate.id == StepDefinition.template_id)
            .join(Employee, Employee.id == ProductStep.performed_by_id)
            .where(
                ProductStep.status == StepStatus.done,
                ProductStep.performed_at >= period_start,
                ProductStep.performed_at < period_end,
            )
        )

        if employee_id is not None:
            stmt = stmt.where(ProductStep.performed_by_id == employee_id)

        stmt = stmt.group_by(
            Product.process_id,
            Process.name,
            Process.size_type_id,
            SizeType.name,
            ProductStep.step_definition_id,
            StepDefinition.order,
            StepTemplate.name,
            ProductStep.performed_by_id,
            Employee.name,
        )

        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def get_completed_steps_by_day(
            self,
            date_from: date_type,
            date_to: date_type,
            employee_id: int | None = None,
    ) -> list[dict]:
        """
        Возвращает число выполненных этапов по дням для каждой комбинации:
        (employee_id, step_definition_id, day).

        Условие периода использует исходный performed_at, поэтому индекс по
        performed_at остаётся применимым. func.date применяется только для
        группировки по производственному календарному дню.
        """
        period_start, period_end = _make_datetime_period(date_from, date_to)

        # Важно: PostgreSQL для timestamptz вычисляет date(...) в TimeZone сессии.
        # Для фиксированной бизнес-зоны группировку нужно явно привязать к MSK.
        day_expr = func.date(
            ProductStep.performed_at.op("AT TIME ZONE")("Europe/Moscow")
        )

        stmt = (
            select(
                ProductStep.performed_by_id.label("employee_id"),
                ProductStep.step_definition_id,
                day_expr.label("day"),
                func.count(ProductStep.id).label("count"),
            )
            .where(
                ProductStep.status == StepStatus.done,
                ProductStep.performed_at >= period_start,
                ProductStep.performed_at < period_end,
                )
        )

        if employee_id is not None:
            stmt = stmt.where(ProductStep.performed_by_id == employee_id)

        stmt = stmt.group_by(
            ProductStep.performed_by_id,
            ProductStep.step_definition_id,
            day_expr,
        )

        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def list_by_process_and_last_completed_step(
        self,
        *,
        process_id: int,
        step_definition_id: int,
    ) -> list[Product]:
        last_step_id_subq = (
            select(ProductStep.id)
            .join(StepDefinition, StepDefinition.id == ProductStep.step_definition_id)
            .where(ProductStep.product_id == Product.id)  # корреляция с outer query
            .where(ProductStep.performed_at.is_not(None))
            .order_by(
                desc(StepDefinition.order),
                desc(ProductStep.performed_at),
                desc(ProductStep.id),
            )
            .limit(1)
            .correlate(Product)
            .scalar_subquery()
        )

        stmt = (
            select(Product)
            .options(
                joinedload(Product.work_process),
                joinedload(Product.steps)
                .joinedload(ProductStep.step_definition)
                .joinedload(StepDefinition.template),
                joinedload(Product.steps).joinedload(ProductStep.performed_by),
            )
            .where(Product.process_id == process_id)
            .where(Product.packaging_id.is_(None))
            .where(Product.status == ProductStatus.normal)
            .where(
                select(ProductStep.step_definition_id)
                .where(ProductStep.id == last_step_id_subq)
                .scalar_subquery()
                == step_definition_id
            )
            .order_by(Product.id)
        )

        result = await self.session.scalars(stmt)
        return result.unique().all()

    async def list_by_step_employee_and_day(
        self,
        *,
        step_definition_id: int,
        employee_id: int,
        day: date_type,
    ) -> list[Product]:
        """
        Продукты, у которых ЕСТЬ этап с указанным step_definition_id,
        выполненный заданным сотрудником в указанную дату.
        """
        has_step_subq = (
            select(ProductStep.id)
            .where(
                ProductStep.product_id == Product.id,
                ProductStep.step_definition_id == step_definition_id,
                ProductStep.performed_by_id == employee_id,
                ProductStep.status == StepStatus.done,
                ProductStep.performed_at >= day,
                ProductStep.performed_at < day + timedelta(days=1),
            )
            .exists()
        )

        stmt = (
            select(Product)
            .options(
                joinedload(Product.work_process),
                joinedload(Product.steps)
                .joinedload(ProductStep.step_definition)
                .joinedload(StepDefinition.template),
                joinedload(Product.steps).joinedload(ProductStep.performed_by),
            )
            .where(has_step_subq)
            .order_by(Product.id)
        )

        result = await self.session.scalars(stmt)
        return result.unique().all()

    async def get_products_not_normal(self) -> list[Product]:
        """
        Возвращает список продуктов, статус которых отличается от ProductStatus.normal.
        """
        stmt = (
            select(Product)
            .where(Product.status != ProductStatus.normal)
            .options(
                joinedload(Product.work_process),
                joinedload(Product.steps)
                .joinedload(ProductStep.step_definition)
                .joinedload(StepDefinition.template),
                joinedload(Product.steps).joinedload(ProductStep.performed_by),
            )
            .order_by(Product.id)
        )

        result = await self.session.scalars(stmt)
        return list(result.unique().all())
