from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, desc, func, or_
from sqlalchemy.orm import selectinload, aliased

from app.database import Product
from app.database import SessionDep, StepDefinition
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import Inventory, InventoryItem
from app.database.models import Packaging
from app.database.models.product_step import StepStatus, ProductStep


def get_inventory_repo(session: SessionDep) -> "InventoryRepository":
    return InventoryRepository(session)


class InventoryRepository(GetBackNextIdMixin[Inventory]):
    model = Inventory

    async def create_inventory(self, created_by: int) -> Inventory:
        inventory = Inventory(
            created_by_id=created_by,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(inventory)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(inventory)
        return inventory

    async def get_inventory_by_id(self, inventory_id: int) -> Inventory:
        stmt = (
            select(Inventory)
            .options(
                selectinload(Inventory.created_by),
            )
            .where(Inventory.id == inventory_id)
        )
        inventory = await self.session.scalar(stmt)
        if inventory is None:
            raise HTTPException(
                status_code=404,
                detail=f"Инвентаризация с id={inventory_id} не найдена",
            )
        return inventory

    async def complete_inventory(self, inventory_id: int) -> Inventory:
        inventory = await self.get_inventory_by_id(inventory_id)
        if inventory.completed_at is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Инвентаризация {inventory_id} уже завершена",
            )
        inventory.completed_at = datetime.now(timezone.utc)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(inventory)
        return inventory

    async def get_all_inventories(self) -> list[dict]:
        stmt = (
            select(
                Inventory.id,
                Inventory.created_at,
                Inventory.completed_at,
                Inventory.created_by_id,
                func.count(InventoryItem.id).label("item_count"),
            )
            .outerjoin(InventoryItem, InventoryItem.inventory_id == Inventory.id)
            .group_by(
                Inventory.id,
                Inventory.created_at,
                Inventory.completed_at,
                Inventory.created_by_id,
            )
            .order_by(desc(Inventory.created_at))
        )

        result = await self.session.execute(stmt)
        return [
            {
                "id": row.id,
                "created_at": row.created_at,
                "completed_at": row.completed_at,
                "created_by_id": row.created_by_id,
                "item_count": row.item_count,
            }
            for row in result.all()
        ]

    async def add_item(
        self,
        inventory_id: int,
        serial_number: str,
        step_definition_id: int,
    ) -> InventoryItem:
        inventory = await self.get_inventory_by_id(inventory_id)
        if inventory.completed_at is not None:
            raise HTTPException(
                status_code=409,
                detail="Нельзя добавлять позиции в завершённую инвентаризацию",
            )

        stmt = select(InventoryItem).where(
            InventoryItem.inventory_id == inventory_id,
            InventoryItem.serial_number == serial_number,
        )
        result = await self.session.execute(stmt)
        existing_item = result.scalar_one_or_none()

        current_time = datetime.now(timezone.utc)

        if existing_item:
            existing_item.step_definition_id = step_definition_id
            existing_item.scanned_at = current_time
            item = existing_item
        else:
            item = InventoryItem(
                inventory_id=inventory_id,
                serial_number=serial_number,
                step_definition_id=step_definition_id,
                scanned_at=current_time,
            )
            self.session.add(item)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # Перезапрашиваем объект со всеми нужными связями для корректной сериализации
        stmt_refresh = (
            select(InventoryItem)
            .where(InventoryItem.id == item.id)
            .options(
                selectinload(InventoryItem.step_definition).selectinload(
                    StepDefinition.template
                ),
                selectinload(InventoryItem.step_definition).selectinload(
                    StepDefinition.work_process
                ),
            )
        )
        refreshed_item = await self.session.scalar(stmt_refresh)
        return refreshed_item

    async def remove_item(self, inventory_id: int, serial_number: str) -> None:
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.inventory_id == inventory_id)
            .where(InventoryItem.serial_number == serial_number)
        )
        item = await self.session.scalar(stmt)
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Изделие {serial_number} не найдено в инвентаризации",
            )
        await self.session.delete(item)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def get_items(self, inventory_id: int) -> list[InventoryItem]:
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.inventory_id == inventory_id)
            .options(
                selectinload(InventoryItem.step_definition).selectinload(
                    StepDefinition.template
                ),
                selectinload(InventoryItem.step_definition).selectinload(
                    StepDefinition.work_process
                ),
            )
            .order_by(desc(InventoryItem.scanned_at))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def compare(self, inventory_id: int) -> list[dict]:
        inventory = await self.get_inventory_by_id(inventory_id)

        stmt_items = (
            select(InventoryItem)
            .where(InventoryItem.inventory_id == inventory_id)
            .options(
                selectinload(InventoryItem.step_definition).selectinload(
                    StepDefinition.template
                ),
                selectinload(InventoryItem.step_definition).selectinload(
                    StepDefinition.work_process
                ),
            )
        )
        items = (await self.session.scalars(stmt_items)).all()
        if not items:
            return []

        snapshot_at = inventory.completed_at or max(item.scanned_at for item in items)

        # Собираем данные по инвентаризации в простой маппинг по серийнику
        scanned_items_by_serial = {item.serial_number: item for item in items}
        scanned_serials = set(scanned_items_by_serial.keys())

        ps_alias = aliased(ProductStep)
        sd_alias = aliased(StepDefinition)
        pkg_alias = aliased(Packaging)

        last_step_def_id_subq = (
            select(ps_alias.step_definition_id)
            .join(sd_alias, sd_alias.id == ps_alias.step_definition_id)
            .where(ps_alias.product_id == Product.id)
            .where(ps_alias.status == StepStatus.done)
            .where(ps_alias.performed_at.is_not(None))
            .where(ps_alias.performed_at <= snapshot_at)
            .order_by(
                desc(sd_alias.order),
                desc(ps_alias.performed_at),
                desc(ps_alias.id),
            )
            .limit(1)
            .correlate(Product)
            .scalar_subquery()
        )

        is_packaged_at_snapshot_expr = (
            select(1)
            .where(pkg_alias.id == Product.packaging_id)
            .where(pkg_alias.performed_at.is_not(None))
            .where(pkg_alias.performed_at <= snapshot_at)
            .correlate(Product)
            .exists()
        )

        # Условие выборки: продукт не упакован ИЛИ отсканирован в ходе этой инвентаризации
        condition = ~is_packaged_at_snapshot_expr
        if scanned_serials:
            condition = or_(condition, Product.serial_number.in_(scanned_serials))

        stmt_products = select(
            Product,
            last_step_def_id_subq.label("current_step_definition_id"),
            is_packaged_at_snapshot_expr.label("is_packaged_at_snapshot"),
        ).where(condition)

        db_rows = (await self.session.execute(stmt_products)).all()

        products_from_inventory_by_serial: dict[str, Product] = {}
        accounting_info_by_serial: dict[str, tuple[Product, int]] = {}
        all_product_ids: set[int] = set()

        for product, current_step_definition_id, is_packaged_at_snapshot in db_rows:
            all_product_ids.add(product.id)

            if product.serial_number in scanned_serials:
                products_from_inventory_by_serial[product.serial_number] = product

            if not is_packaged_at_snapshot and current_step_definition_id is not None:
                accounting_info_by_serial[product.serial_number] = (
                    product,
                    current_step_definition_id,
                )

        product_step_dates: dict[tuple[int, int], datetime] = {}
        if all_product_ids:
            stmt_steps_dates = select(
                ProductStep.product_id,
                ProductStep.step_definition_id,
                ProductStep.performed_at,
            ).where(
                ProductStep.product_id.in_(all_product_ids),
                ProductStep.status == StepStatus.done,
                ProductStep.performed_at.is_not(None),
                ProductStep.performed_at <= snapshot_at,
            )
            steps_rows = (await self.session.execute(stmt_steps_dates)).all()
            for p_id, sd_id, perf_at in steps_rows:
                product_step_dates[(p_id, sd_id)] = perf_at

        # Собираем все уникальные ID этапов из обоих источников для одного запроса
        all_step_ids = {
            item.step_definition_id
            for item in items
            if item.step_definition_id is not None
        } | {step_id for _, step_id in accounting_info_by_serial.values()}

        step_def_map = {}
        if all_step_ids:
            stmt_step_defs = (
                select(StepDefinition)
                .where(StepDefinition.id.in_(all_step_ids))
                .options(
                    selectinload(StepDefinition.template),
                    selectinload(StepDefinition.work_process),
                )
            )
            step_defs = await self.session.scalars(stmt_step_defs)
            step_def_map = {sd.id: sd for sd in step_defs.unique().all()}

        all_serials = scanned_serials | set(accounting_info_by_serial.keys())
        results = []

        for serial in sorted(all_serials):
            scanned_item = scanned_items_by_serial.get(serial)
            accounting_info = accounting_info_by_serial.get(serial)

            # Вытаскиваем этап по инвентаризации
            inventory_step_def = None
            if scanned_item and scanned_item.step_definition_id:
                inventory_step_def = step_def_map.get(scanned_item.step_definition_id)

            accounting_step_def = None
            perf_at = None

            if accounting_info:
                product, acc_step_id = accounting_info
                accounting_step_def = step_def_map.get(acc_step_id)
                perf_at = product_step_dates.get((product.id, acc_step_id))
            else:
                # Если товара нет в учёте на каком-либо этапе (или он упакован),
                # он гарантированно берется из отсканированных (через or_)
                product = products_from_inventory_by_serial.get(serial)

            # product.id if product else None оставлено для сверхнадежности на случай фантомных записей
            results.append(
                {
                    "id": product.id if product else None,
                    "serial_number": serial,
                    "status": product.status if product else None,
                    "inventory_step_definition": inventory_step_def,
                    "accounting_step_definition": accounting_step_def,
                    "performed_at": perf_at,
                }
            )

        return results
