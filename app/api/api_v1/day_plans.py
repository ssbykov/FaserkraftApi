from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.api_v1.fastapi_users import current_user
from app.database.crud.daily_plans import DailyPlanRepository, get_daily_plan_repo
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.models import User
from app.database.models.employee import Role
from app.database.schemas.daily_plan import DailyPlanRead
from app.database.schemas.daily_plan_step import (
    DailyPlanStepCreate,
    DailyPlanStepUpdate,
)

router = APIRouter(prefix="/daily-plans", tags=["daily-plans"])


@router.get(
    "",
    response_model=list[DailyPlanRead],
    status_code=status.HTTP_200_OK,
)
async def get_daily_plans(
    plan_date: date,
    repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> list[DailyPlanRead]:
    try:
        employee = await employee_repo.get_by_user_id(user.id)
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


@router.post(
    "/add_step",
    response_model=list[DailyPlanRead],
    status_code=status.HTTP_200_OK,
)
async def add_step_to_daily_plan(
    payload: DailyPlanStepCreate,
    repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> list[DailyPlanRead]:
    try:
        employee = await employee_repo.get_by_user_id(user.id)

        if not employee.role in [Role.admin, Role.master]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав доступа к этому ресурсу",
            )

        employee_id = payload.employee_id
        plan_date = payload.plan_date
        await repo.add_step_to_daily_plan(
            date=plan_date,
            employee_id=employee_id,
            step_id=payload.step_id,
            planned_quantity=payload.planned_quantity,
        )

        # берём актуальный план (с подгруженными steps)
        daily_plans = await repo.get(date=payload.plan_date)
        if not daily_plans:
            raise HTTPException(
                status_code=404,
                detail="План на указанную дату не найден",
            )

        return [DailyPlanRead.model_validate(dp) for dp in daily_plans]

    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при добавлении этапа в план",
        )


@router.post(
    "/update_step",
    response_model=list[DailyPlanRead],
    status_code=status.HTTP_200_OK,
)
async def update_step_in_daily_plan(
    payload: DailyPlanStepUpdate,  # новая схема с id шага
    repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> list[DailyPlanRead]:
    try:
        employee = await employee_repo.get_by_user_id(user.id)

        if employee.role not in [Role.admin, Role.master]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав доступа к этому ресурсу",
            )

        await repo.update_step_in_daily_plan(
            step_id=payload.step_id,
            date=payload.plan_date,
            employee_id=payload.employee_id,
            step_definition_id=payload.step_definition_id,
            planned_quantity=payload.planned_quantity,
        )

        daily_plans = await repo.get(date=payload.plan_date)
        if not daily_plans:
            raise HTTPException(
                status_code=404,
                detail="План на указанную дату не найден",
            )

        return [DailyPlanRead.model_validate(dp) for dp in daily_plans]

    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при обновлении этапа в плане",
        )


@router.delete(
    "/steps/{daily_plan_step_id}",
    response_model=list[DailyPlanRead],
    status_code=status.HTTP_200_OK,
)
async def remove_step_from_daily_plan(
    daily_plan_step_id: int,
    repo: Annotated[DailyPlanRepository, Depends(get_daily_plan_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> list[DailyPlanRead]:
    try:
        employee = await employee_repo.get_by_user_id(user.id)

        if employee.role not in [Role.admin, Role.master]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав доступа к этому ресурсу",
            )

        daily_plans = await repo.remove_step_from_daily_plan(
            daily_plan_step_id=daily_plan_step_id,
        )

        if not daily_plans:
            raise HTTPException(
                status_code=404,
                detail="План или этап не найден",
            )

        return [DailyPlanRead.model_validate(dp) for dp in daily_plans]

    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при удалении этапа из плана",
        )
