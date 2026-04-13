from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.core import settings
from app.database.crud.orders import OrderRepository, get_order_repo
from app.database.schemas.order import (
    OrderRead,
    OrderCreate,
    OrderUpdate,
    OrderItemCreate,
    OrderClose
)
from app.database.schemas.employee import EmployeeRead

from app.api.api_v1.dependencies import get_current_employee, require_admin_or_master


router = APIRouter(
    tags=["Orders"],
    prefix=settings.api.v1.orders,
)


@router.get(
    "/get_all_orders",
    response_model=list[OrderRead],
    status_code=status.HTTP_200_OK,
)
async def get_all_orders(
        repo: Annotated[OrderRepository, Depends(get_order_repo)],
        employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> list[OrderRead]:
    try:
        orders = await repo.get_all()
        return [OrderRead.model_validate(p) for p in orders]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении заказов",
        )


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
        data: OrderCreate,
        repo: Annotated[OrderRepository, Depends(get_order_repo)],
        employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> OrderRead:
    try:
        order = await repo.create(order_in=data)
        return OrderRead.model_validate(order)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при создании заказа",
        )


@router.put(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_200_OK,
)
async def update_order(
        data: OrderUpdate,
        repo: Annotated[OrderRepository, Depends(get_order_repo)],
        employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> OrderRead:
    """Обновление основных данных заказа (идентификатор передается в теле запроса)"""
    try:
        order = await repo.update(order_in=data)
        return OrderRead.model_validate(order)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при обновлении заказа",
        )


@router.put(
    "/{order_id}/items",
    response_model=OrderRead,
    status_code=status.HTTP_200_OK,
)
async def update_order_items(
        order_id: int,
        items: list[OrderItemCreate],
        repo: Annotated[OrderRepository, Depends(get_order_repo)],
        employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> OrderRead:
    """Полная перезапись состава (позиций) заказа"""
    try:
        order = await repo.update_items(order_id=order_id, items_in=items)
        return OrderRead.model_validate(order)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при обновлении состава заказа",
        )


@router.post(
    "/{order_id}/close",
    response_model=OrderRead,
    status_code=status.HTTP_200_OK,
)
async def close_order(
        order_id: int,
        data: OrderClose,
        repo: Annotated[OrderRepository, Depends(get_order_repo)],
        employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> OrderRead:
    """Закрытие (отгрузка) заказа с простановкой даты и ответственного сотрудника"""
    try:
        order = await repo.close(order_id=order_id, close_in=data)
        return OrderRead.model_validate(order)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при закрытии заказа",
        )


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    status_code=status.HTTP_200_OK,
)
async def get_order(
        order_id: int,
        repo: Annotated[OrderRepository, Depends(get_order_repo)],
        employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> OrderRead:
    try:
        order = await repo.get_by_id(obj_id=order_id)
        return OrderRead.model_validate(order)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении заказа",
        )


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_order(
        order_id: int,
        repo: Annotated[OrderRepository, Depends(get_order_repo)],
        employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> None:
    try:
        await repo.delete(id=order_id)
        return
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при удалении заказа",
        )