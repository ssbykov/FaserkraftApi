from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.core import settings
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.crud.products import get_product_repo, ProductRepository
from app.database.crud.products_steps import (
    ProductStepRepository,
    get_products_steps_repo,
)
from app.database.models import User
from app.database.models.product_step import StepStatus
from app.database.schemas.product import ProductRead

router = APIRouter(
    tags=["Products_Steps"],
    prefix=settings.api.v1.products_steps,
)
router.include_router(
    router,
)


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def accept_step(
    step_id: int,
    repo: Annotated[ProductStepRepository, Depends(get_products_steps_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    product_repo: Annotated[ProductRepository, Depends(get_product_repo)],
    user: Annotated[User, Depends(current_user)],
) -> Optional[ProductRead]:
    try:
        employee = await employee_repo.get_by_id(user.id)
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
