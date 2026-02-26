from datetime import date
from functools import partial
from typing import Annotated, Callable, Awaitable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.core import settings
from app.database import Product
from app.database.crud.daily_plans import DailyPlanRepository, get_daily_plan_repo
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.crud.processes import ProcessRepository, get_process_repo
from app.database.crud.products import ProductRepository, get_product_repo
from app.database.models import User
from app.database.models.employee import Role
from app.database.models.product import ProductStatus
from app.database.schemas.product import ProductRead, ProductCreate

router = APIRouter(
    tags=["Products"],
    prefix=settings.api.v1.products,
)
router.include_router(
    router,
)


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    process_repo: Annotated[ProcessRepository, Depends(get_process_repo)],
    day_plan_repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    user: Annotated[User, Depends(current_user)],
) -> ProductRead:
    try:
        employee = await employee_repo.get_by_user_id(user.id)
        first_step = await process_repo.get_first_step(product_in.process_id)

        if not await day_plan_repo.check_step_def_in_daily_plan(
            date=date.today(),
            employee_id=employee.id,
            step_def_id=first_step.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="В планах нет этого этапа"
            )

        product = await repo.create_product(product_in)
        return ProductRead.model_validate(product)

    except IntegrityError as e:
        msg = str(e.orig)

        # FK на process_id
        if (
            "violates foreign key constraint" in msg
            or "ForeignKeyViolationError" in msg
            or "foreign key" in msg.lower()
        ):
            raise HTTPException(
                status_code=422,
                detail="Указан несуществующий process_id",
            )

        # уникальность по serial_number
        if (
            "duplicate key value" in msg
            or "уже существует" in msg
            or "unique constraint" in msg.lower()
        ):
            raise HTTPException(
                status_code=409,
                detail="Продукт с таким серийным номером уже существует",
            )

        # прочие ошибки целостности без утечки текста SQL
        raise HTTPException(
            status_code=400,
            detail="Ошибка целостности данных при создании продукта",
        )

    except ValueError as e:
        # например, если в repo.create_product ты явно кинул,
        # что процесс не найден
        raise HTTPException(status_code=422, detail=str(e))

    except HTTPException:
        # если repo сам кинул HTTPException — просто пробрасываем
        raise

    except Exception:
        # внутренняя ошибка без деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при создании продукта",
        )


@router.get(
    "/{serial_number}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def get_product(
    serial_number: str,
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    user: Annotated[User, Depends(current_user)],
) -> ProductRead:
    try:
        product = await repo.get(serial_number=serial_number)
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продукта",
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
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> ProductRead:
    try:
        employee = await employee_repo.get_by_user_id(user.id)
        if employee.role not in [Role.admin, Role.master]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данная операция недоступна",
            )

        product = await repo.change_product_process(
            product_id=product_id, new_process_id=new_process_id
        )
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продукта",
        )


@router.post(
    "/{product_id}/change_status",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def change_product_status(
    product_id: int,
    status: ProductStatus,  # ?status=scrap|rework|normal
    repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> ProductRead:
    return await _change_product_status_route(
        product_id=product_id,
        status_change_call=partial(repo.set_status, status=status),
        employee_repo=employee_repo,
        user=user,
    )


async def _change_product_status_route(
    product_id: int,
    status_change_call: Callable[[int], Awaitable[Product]],
    employee_repo: EmployeeRepository,
    user: User,
) -> ProductRead:
    try:
        employee = await employee_repo.get_by_user_id(user.id)
        if employee.role not in [Role.admin, Role.master]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данная операция недоступна",
            )

        product = await status_change_call(product_id)
        return ProductRead.model_validate(product)
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при изменении статуса продукта",
        )
