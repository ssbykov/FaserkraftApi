from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from app.core import settings
from app.database.crud.products_steps import (
    ProductStepRepository,
    get_products_steps_repo,
)
from app.database.schemas.product_step import ProductStepUpdate

router = APIRouter(
    tags=["Products_Steps"],
    prefix=settings.api.v1.products_steps,
)
router.include_router(
    router,
)


@router.post("/", response_model=ProductStepUpdate, status_code=status.HTTP_201_CREATED)
async def accept_step(
    step_id: int,
    employee_id: int,
    repo: Annotated[ProductStepRepository, Depends(get_products_steps_repo)],
) -> ProductStepUpdate:
    try:
        step = await repo.accept_step(step_id, employee_id)
        if step is None:
            raise HTTPException(status_code=404, detail="Шаг не найден")
        return ProductStepUpdate.model_validate(step)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Произошла внутренняя ошибка")
