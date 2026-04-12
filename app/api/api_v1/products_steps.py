from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.api.api_v1.dependencies import get_current_employee
from app.core import settings
from app.database.crud.daily_plans import DailyPlanRepository, get_daily_plan_repo
from app.database.crud.products import get_product_repo, ProductRepository
from app.database.crud.products_steps import (
    ProductStepRepository,
    get_products_steps_repo,
)
from app.database.models.employee import Role
from app.database.models.product_step import StepStatus
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.product import ProductRead

router = APIRouter(
    tags=["Products_Steps"],
    prefix=settings.api.v1.products_steps,
)


@router.post(
    "/",
    response_model=ProductRead | None,  # Разрешаем возврат None на уровне схемы ответа
    status_code=status.HTTP_201_CREATED,
)
async def accept_step(
    step_id: int,
    repo: Annotated[ProductStepRepository, Depends(get_products_steps_repo)],
    day_plan_repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    product_repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
    plan_date: date | None = None,
) -> Optional[ProductRead]:
    try:
        # Учли и admin, и master
        if (
            employee.role not in [Role.admin, Role.master]
            and not await day_plan_repo.check_step_in_daily_plan(
                date=plan_date if plan_date else date.today(),
                employee_id=employee.id,
                product_step_id=step_id,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="В планах нет этого этапа",
            )

        step = await repo.accept_step(step_id, employee.id)
        if step is None:
            raise HTTPException(status_code=404, detail="Шаг не найден")

        if step.status == StepStatus.done:
            product = await product_repo.get(id=step.product_id)
            return ProductRead.model_validate(product)

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Произошла внутренняя ошибка {e}")


@router.post(
    "/change_performer",
    response_model=ProductRead | None,  # Разрешаем возврат None
    status_code=status.HTTP_200_OK,
)
async def change_step_performer(
    step_id: int,
    new_employee_id: int,
    repo: Annotated[ProductStepRepository, Depends(get_products_steps_repo)],
    day_plan_repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    product_repo: Annotated[ProductRepository, Depends(get_product_repo)],
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
    plan_date: date | None = None,
) -> Optional[ProductRead]:
    try:
        if (
            employee.role not in [Role.admin, Role.master]
            and not await day_plan_repo.check_step_in_daily_plan(
                date=plan_date if plan_date else date.today(),
                employee_id=employee.id,
                product_step_id=step_id,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="В планах нет этого этапа",
            )

        # смена исполнителя (только если этап закрыт)
        step = await repo.change_performer_if_done(step_id, new_employee_id)
        if step is None:
            raise HTTPException(status_code=404, detail="Шаг не найден")

        product = await product_repo.get(id=step.product_id)
        return ProductRead.model_validate(product)

    except HTTPException:
        raise
    except ValueError as e:
        # ошибка из репозитория, если статус не done
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Произошла внутренняя ошибка {e}",
        )