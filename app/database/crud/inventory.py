from datetime import datetime, timezone
from itertools import groupby

from fastapi import HTTPException
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, aliased

from app.database import SessionDep, StepDefinition
from app.database.models.product import ProductStatus
from app.database.models.product_step import StepStatus
from app.database import Product, ProductStep
from app.database.models import Inventory, InventoryItem
from app.database.crud.mixines import GetBackNextIdMixin


def get_inventory_repo(session: SessionDep) -> "InventoryRepository":
    return InventoryRepository(session)


class InventoryRepository(GetBackNextIdMixin[Inventory]):
    model = Inventory

    # ---------- Inventory ----------

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

    async def get_inventory(self, inventory_id: int) -> Inventory:
        stmt = select(Inventory).where(Inventory.id == inventory_id)
        inventory = await self.session.scalar(stmt)
        if inventory is None:
            raise HTTPException(
                status_code=404,
                detail=f"Инвентаризация с id={inventory_id} не найдена",
            )
        return inventory

    async def complete_inventory(self, inventory_id: int) -> Inventory:
        inventory = await self.get_inventory(inventory_id)
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

    async def get_all_inventories(self) -> list[Inventory]:
        stmt = select(Inventory).order_by(desc(Inventory.created_at))
        result = await self.session.scalars(stmt)
        return list(result.all())

    # ---------- InventoryItem ----------

    async def add_item(
        self,
        inventory_id: int,
        serial_number: str,
        step_definition_id: int,
    ) -> InventoryItem:
        inventory = await self.get_inventory(inventory_id)
        if inventory.completed_at is not None:
            raise HTTPException(
                status_code=409,
                detail="Нельзя добавлять позиции в завершённую инвентаризацию",
            )

        item = InventoryItem(
            inventory_id=inventory_id,
            serial_number=serial_number,
            step_definition_id=step_definition_id,
            scanned_at=datetime.now(timezone.utc),
        )
        self.session.add(item)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Изделие {serial_number} уже добавлено в эту инвентаризацию",
            )
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(item)
        return item

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
                joinedload(InventoryItem.step_definition).joinedload(
                    StepDefinition.template
                )
            )
            .order_by(InventoryItem.scanned_at)
        )
        result = await self.session.scalars(stmt)
        return list(result.unique().all())

    # ---------- Compare ----------

    async def compare(self, inventory_id: int) -> list[dict]:
        items = await self.get_items(inventory_id)
        items_sorted = sorted(items, key=lambda x: x.step_definition_id)

        all_step_ids = list({i.step_definition_id for i in items_sorted})
        stmt_all_sd = (
            select(StepDefinition)
            .where(StepDefinition.id.in_(all_step_ids))
            .options(joinedload(StepDefinition.template))
        )
        step_defs = await self.session.scalars(stmt_all_sd)
        step_def_map = {sd.id: sd for sd in step_defs.unique().all()}

        # Алиасы создаём один раз за пределами цикла
        ps_alias = aliased(ProductStep)
        sd_alias = aliased(StepDefinition)

        # Подзапрос: id последнего выполненного ProductStep для каждого Product
        last_step_id_subq = (
            select(ps_alias.id)
            .join(sd_alias, sd_alias.id == ps_alias.step_definition_id)
            .where(ps_alias.product_id == Product.id)
            .where(ps_alias.status == StepStatus.done)
            .order_by(
                desc(sd_alias.order),
                desc(ps_alias.performed_at),
                desc(ps_alias.id),
            )
            .limit(1)
            .correlate(Product)
            .scalar_subquery()
        )

        # Подзапрос: step_definition_id последнего шага
        last_step_def_id_subq = (
            select(ps_alias.step_definition_id)
            .where(ps_alias.id == last_step_id_subq)
            .scalar_subquery()
        )

        results = []
        for step_def_id, group_iter in groupby(
            items_sorted, key=lambda x: x.step_definition_id
        ):
            scanned_items = list(group_iter)
            scanned_serials = {i.serial_number for i in scanned_items}
            step_def = step_def_map.get(step_def_id)

            # Изделия без упаковки, у которых последний шаг == step_def_id
            stmt_db = (
                select(Product.serial_number)
                .where(Product.packaging_id.is_(None))
                .where(Product.status == ProductStatus.normal)
                .where(last_step_def_id_subq == step_def_id)
            )
            result_db = await self.session.execute(stmt_db)
            db_serials = {row.serial_number for row in result_db.all()}

            results.append(
                {
                    "step_definition_id": step_def_id,
                    "step_name": step_def.template.name if step_def else None,
                    "process_id": step_def.process_id if step_def else None,
                    "db_count": len(db_serials),
                    "scanned_count": len(scanned_serials),
                    "matched": sorted(scanned_serials & db_serials),
                    "missing": sorted(db_serials - scanned_serials),
                    "unexpected": sorted(scanned_serials - db_serials),
                }
            )

        return results
