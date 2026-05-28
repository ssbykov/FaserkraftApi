from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, desc, func, or_
from sqlalchemy.orm import selectinload, aliased, joinedload

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
        # 1. Загружаем строки инвентаризации
        stmt_items = (
            select(InventoryItem)
            .where(InventoryItem.inventory_id == inventory_id)
            .options(joinedload(InventoryItem.step_definition))
        )
        items = (await self.session.scalars(stmt_items)).all()
        if not items:
            return []

        snapshot_at = max(item.scanned_at for item in items)
        scanned_serials = {item.serial_number for item in items}

        scanned_items_by_step: dict[int, dict[str, InventoryItem]] = defaultdict(dict)
        for item in items:
            scanned_items_by_step[item.step_definition_id][item.serial_number] = item

        ps_alias = aliased(ProductStep)
        sd_alias = aliased(StepDefinition)
        pkg_alias = aliased(Packaging)

        # Последний завершенный шаг на момент snapshot_at
        last_step_id_subq = (
            select(ps_alias.id)
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

        last_step_def_id_subq = (
            select(ps_alias.step_definition_id)
            .where(ps_alias.id == last_step_id_subq)
            .scalar_subquery()
        )

        # Упакован ли продукт на snapshot_at
        is_packaged_at_snapshot_expr = (
            select(1)
            .where(pkg_alias.id == Product.packaging_id)
            .where(pkg_alias.performed_at.is_not(None))
            .where(pkg_alias.performed_at <= snapshot_at)
            .correlate(Product)
            .exists()
        )

        # 2. Берем:
        # - все продукты из инвентаризации
        # - все продукты, не упакованные на snapshot_at
        product_filters = [~is_packaged_at_snapshot_expr]
        if scanned_serials:
            product_filters.append(Product.serial_number.in_(scanned_serials))

        stmt_products = select(
            Product,
            last_step_def_id_subq.label("current_step_definition_id"),
            is_packaged_at_snapshot_expr.label("is_packaged_at_snapshot"),
        ).where(or_(*product_filters))
        db_rows = (await self.session.execute(stmt_products)).all()

        # 3. Разделяем:
        # - все продукты из инвентаризации по serial
        # - учетные продукты (не упакованные на snapshot_at) по этапу
        products_from_inventory_by_serial: dict[str, Product] = {}
        accounting_products_by_step: dict[int, dict[str, Product]] = defaultdict(dict)

        for product, current_step_definition_id, is_packaged_at_snapshot in db_rows:
            if product.serial_number in scanned_serials:
                products_from_inventory_by_serial[product.serial_number] = product

            if not is_packaged_at_snapshot and current_step_definition_id is not None:
                accounting_products_by_step[current_step_definition_id][
                    product.serial_number
                ] = product

        # 4. Все step_definition_id из физики и учета
        all_step_ids = set(scanned_items_by_step.keys()) | set(
            accounting_products_by_step.keys()
        )
        if not all_step_ids:
            return []

        stmt_step_defs = (
            select(StepDefinition)
            .where(StepDefinition.id.in_(all_step_ids))
            .options(
                joinedload(StepDefinition.template),
                joinedload(StepDefinition.work_process),
            )
        )
        step_defs = await self.session.scalars(stmt_step_defs)
        step_def_map = {sd.id: sd for sd in step_defs.unique().all()}

        def make_item(product: Product, step_def: StepDefinition) -> dict:
            return {
                "id": product.id,
                "serial_number": product.serial_number,
                "status": product.status,
                "step_definition": step_def,
            }

        results = []

        for step_def_id in sorted(
            all_step_ids,
            key=lambda sid: (
                (
                    step_def_map[sid].work_process.id
                    if sid in step_def_map and step_def_map[sid].work_process
                    else 0
                ),
                step_def_map[sid].order if sid in step_def_map else 0,
                sid,
            ),
        ):
            step_def = step_def_map.get(step_def_id)
            if step_def is None:
                continue

            scanned_map = scanned_items_by_step.get(step_def_id, {})
            scanned_serials_step = set(scanned_map.keys())

            accounting_map = accounting_products_by_step.get(step_def_id, {})
            accounting_serials_step = set(accounting_map.keys())

            matched_serials = scanned_serials_step & accounting_serials_step
            missing_serials = accounting_serials_step - scanned_serials_step
            unexpected_serials = scanned_serials_step - accounting_serials_step

            matched = [
                make_item(accounting_map[s], step_def) for s in sorted(matched_serials)
            ]

            missing = [
                make_item(accounting_map[s], step_def) for s in sorted(missing_serials)
            ]

            unexpected = [
                make_item(products_from_inventory_by_serial[s], step_def)
                for s in sorted(unexpected_serials)
            ]

            results.append(
                {
                    "db_count": len(accounting_serials_step),
                    "scanned_count": len(scanned_serials_step),
                    "matched": matched,
                    "missing": missing,
                    "unexpected": unexpected,
                }
            )

        return results
