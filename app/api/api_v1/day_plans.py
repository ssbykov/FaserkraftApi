from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.api_v1.fastapi_users import current_user
from app.database.crud.daily_plans import DailyPlanRepository, get_daily_plan_repo
from app.database.models import User
from app.database.schemas.daily_plan import DailyPlanRead

router = APIRouter(prefix="/daily-plans", tags=["daily-plans"])


@router.get(
    "/{employee_id}",
    response_model=DailyPlanRead,
    status_code=status.HTTP_200_OK,
)
async def get_daily_plan(
    employee_id: int,
    plan_date: date,  # ?plan_date=2026-02-07
    repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    user: Annotated[User, Depends(current_user)],
) -> DailyPlanRead:
    try:
        daily_plan = await repo.get(employee_id=employee_id, date=plan_date)
        return DailyPlanRead.model_validate(daily_plan)
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении плана на день",
        )
