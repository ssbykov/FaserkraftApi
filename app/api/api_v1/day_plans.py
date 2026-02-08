from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.api_v1.fastapi_users import current_user
from app.database.crud.daily_plans import DailyPlanRepository, get_daily_plan_repo
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.models import User
from app.database.models.employee import Role
from app.database.schemas.daily_plan import DailyPlanRead

router = APIRouter(prefix="/daily-plans", tags=["daily-plans"])


@router.get(
    "",
    response_model=list[DailyPlanRead],
    status_code=status.HTTP_200_OK,
)
async def get_daily_plans(
    plan_date: date,  # ?plan_date=2026-02-07
    repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> list[DailyPlanRead]:
    try:
        employee = await employee_repo.get_by_id(user.id)
        employee_id = None
        if employee.role not in [Role.admin, Role.master]:
            employee_id = employee.id

        daily_plans = await repo.get(date=plan_date, employee_id=employee_id)
        return [DailyPlanRead.model_validate(dp) for dp in daily_plans]
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении планов на день",
        )
