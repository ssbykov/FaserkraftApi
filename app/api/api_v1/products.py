from datetime import date
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.api.api_v1.dependencies import get_current_employee, require_admin_or_master
from app.core import settings
from app.database.crud.daily_plans import DailyPlanRepository, get_daily_plan_repo
from app.database.crud.processes import ProcessRepository, get_process_repo
from app.database.crud.products import ProductRepository, get_product_repo
from app.database.models.employee import Role
from app.database.models.product import ProductStatus
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.product import (
    ProductRead,
    ProductCreate,
    ProductsCountByLastStepRead,
    ProductsFinishedRead,
)

router = APIRouter(
    tags=["Products"],
    prefix=settings.api.v1.products,
)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    process_repo: Annotated[ProcessRepository, Depends(get_process_repo)],
    day_plan_repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> ProductRead:
    try:
        first_step = await process_repo.get_first_step(product_in.process_id)

        if employee.role not in [
            Role.admin,
            Role.master,
        ] and not await day_plan_repo.check_step_def_in_daily_plan(
            date=date.today(),
            employee_id=employee.id,
            step_def_id=first_step.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="В планах нет этого этапа"
            )

        product = await repo.create_product(product_in)
        return ProductRead.model_validate(product)

    except IntegrityError as e:
        msg = str(e.orig)
        if (
            "violates foreign key constraint" in msg
            or "ForeignKeyViolationError" in msg
            or "foreign key" in msg.lower()
        ):
            raise HTTPException(
                status_code=422, detail="Указан несуществующий process_id"
            )
        if (
            "duplicate key value" in msg
            or "уже существует" in msg
            or "unique constraint" in msg.lower()
        ):
            raise HTTPException(
                status_code=409,
                detail="Продукт с таким серийным номером уже существует",
            )
        raise HTTPException(
            status_code=400, detail="Ошибка целостности данных при создании продукта"
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при создании продукта",
        )


@router.get(
    "/by-serial/{serial_number}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def get_product(
    serial_number: str,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> ProductRead:
    try:
        product = await repo.get(serial_number=serial_number)
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продукта",
        )


@router.get(
    "/stats/by-last-done-step",
    response_model=list[ProductsCountByLastStepRead],
    status_code=status.HTTP_200_OK,
)
async def get_products_stats_by_last_done_step(
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> list[ProductsCountByLastStepRead]:
    try:
        data = await repo.get_counts_by_last_done_step()
        return [ProductsCountByLastStepRead(**item) for item in data]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении статистики по продуктам",
        )


@router.get(
    "/finished",
    response_model=list[ProductsFinishedRead],
    status_code=status.HTTP_200_OK,
)
async def get_finished_products(
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> list[ProductsFinishedRead]:
    try:
        employee_id = None
        if employee.role not in [Role.admin, Role.master]:
            employee_id = employee.id

        products = await repo.get_finished_products(employee_id=employee_id)
        return [ProductsFinishedRead.model_validate(p) for p in products]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении списка завершённых продуктов",
        )


@router.get(
    "/by-step-employee-day",
    response_model=list[ProductRead],
    status_code=status.HTTP_200_OK,
)
async def get_products_by_step_employee_day(
    step_definition_id: int,
    day: date_type,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
    employee_id: int | None = None,
) -> list[ProductRead]:
    try:
        if employee.role not in [Role.admin, Role.master]:
            effective_employee_id = employee.id
        else:
            effective_employee_id = employee_id or employee.id

        products = await repo.list_by_step_employee_and_day(
            step_definition_id=step_definition_id,
            employee_id=effective_employee_id,
            day=day,
        )
        return [ProductRead.model_validate(p) for p in products]

    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продуктов по этапу/сотруднику/дате",
        )


@router.post(
    "/change_product_process",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def change_product_process(
    product_id: int,
    new_process_id: int,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> ProductRead:
    try:
        product = await repo.change_product_process(
            product_id=product_id, new_process_id=new_process_id
        )
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при изменении процесса продукта",
        )


@router.post(
    "/{product_id}/change_status",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def change_product_status(
    product_id: int,
    status: ProductStatus,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> ProductRead:
    try:
        product = await repo.set_status(product_id=product_id, status=status)
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при изменении статуса продукта",
        )


@router.get(
    "/by-last-completed-step",
    response_model=list[ProductRead],
    status_code=status.HTTP_200_OK,
)
async def get_products_by_last_completed_step(
    process_id: int,
    step_definition_id: int,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> list[ProductRead]:
    try:
        products = await repo.list_by_process_and_last_completed_step(
            process_id=process_id,
            step_definition_id=step_definition_id,
        )
        return [ProductRead.model_validate(item) for item in products]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла внутренняя ошибка при получении продуктов",
        )
