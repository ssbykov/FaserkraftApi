from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.api.api_v1.dependencies import require_admin_or_master
from app.core import settings
from app.database.crud.inventory import InventoryRepository, get_inventory_repo
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.inventory import (
    InventoryRead,
    InventoryItemRead,
    InventoryCompareResultRead,
    InventoryListItemOut,
    AddInventoryItemRequest,
)

router = APIRouter(
    tags=["Inventories"],
    prefix=settings.api.v1.inventories,
)


@router.post("", response_model=InventoryRead, status_code=status.HTTP_201_CREATED)
async def create_inventory(
    repo: Annotated[InventoryRepository, Depends(get_inventory_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> InventoryRead:
    try:
        inventory = await repo.create_inventory(created_by=employee.id)
        return InventoryRead.model_validate(inventory)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при создании инвентаризации",
        )


@router.get(
    "", response_model=list[InventoryListItemOut], status_code=status.HTTP_200_OK
)
async def get_all_inventories(
    repo: Annotated[InventoryRepository, Depends(get_inventory_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> list[InventoryListItemOut]:
    try:
        raw_inventories = await repo.get_all_inventories()
        return [InventoryListItemOut.model_validate(i) for i in raw_inventories]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении списка инвентаризаций",
        )


@router.get(
    "/{inventory_id}",
    response_model=InventoryRead,
    status_code=status.HTTP_200_OK,
)
async def get_inventory(
    inventory_id: int,
    repo: Annotated[InventoryRepository, Depends(get_inventory_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> InventoryRead:
    try:
        inventory = await repo.get_inventory_by_id(inventory_id)
        return InventoryRead.model_validate(inventory)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении инвентаризации",
        )


@router.post(
    "/{inventory_id}/complete",
    response_model=InventoryRead,
    status_code=status.HTTP_200_OK,
)
async def complete_inventory(
    inventory_id: int,
    repo: Annotated[InventoryRepository, Depends(get_inventory_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> InventoryRead:
    try:
        inventory = await repo.complete_inventory(inventory_id)
        return InventoryRead.model_validate(inventory)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при завершении инвентаризации",
        )


# ---------- Items ----------


@router.post(
    "/{inventory_id}/items",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_inventory_item(
    inventory_id: int,
    request: AddInventoryItemRequest,
    repo: Annotated[InventoryRepository, Depends(get_inventory_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> InventoryItemRead:
    try:
        item = await repo.add_item(
            inventory_id=inventory_id,
            serial_number=request.serial_number,
            step_definition_id=request.step_definition_id,
        )
        return InventoryItemRead.model_validate(item)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при добавлении позиции",
        )


@router.delete(
    "/{inventory_id}/items/{serial_number}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_inventory_item(
    inventory_id: int,
    serial_number: str,
    repo: Annotated[InventoryRepository, Depends(get_inventory_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> None:
    try:
        await repo.remove_item(
            inventory_id=inventory_id,
            serial_number=serial_number,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при удалении позиции",
        )


@router.get(
    "/{inventory_id}/items",
    response_model=list[InventoryItemRead],
    status_code=status.HTTP_200_OK,
)
async def get_inventory_items(
    inventory_id: int,
    repo: Annotated[InventoryRepository, Depends(get_inventory_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> list[InventoryItemRead]:
    try:
        items = await repo.get_items(inventory_id)
        return [InventoryItemRead.model_validate(i) for i in items]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении позиций инвентаризации",
        )


# ---------- Compare ----------


@router.post(
    "/{inventory_id}/compare",
    response_model=list[InventoryCompareResultRead],
    status_code=status.HTTP_200_OK,
)
async def compare_inventory(
    inventory_id: int,
    repo: Annotated[InventoryRepository, Depends(get_inventory_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> list[InventoryCompareResultRead]:
    try:
        raw_results = await repo.compare(inventory_id)
        return [InventoryCompareResultRead.model_validate(item) for item in raw_results]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при сравнении инвентаризации",
        )
