from typing import List, Annotated, Sequence

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.core import settings
from app.database import Employee
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.models import User
from app.database.models.employee import Role
from app.database.schemas.employee import EmployeeRead
from database.schemas.employee import EmployeeRead

router = APIRouter(
    tags=["Employees"],
    prefix=settings.api.v1.employees,
)

@router.get(
    "/",
    response_model=List[EmployeeRead],
    status_code=status.HTTP_200_OK,
)
async def get_employees(
    repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> Sequence[Employee] | None:
    try:
        employee = await employee_repo.get_by_user_id(user.id)

        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Профиль сотрудника для данного пользователя не найден",
            )

        if employee.role in [Role.admin, Role.master]:
            return await repo.get_all()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав доступа к этому ресурсу",
        )

    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продукта",
        )

# 1. Зависимость для получения профиля сотрудника
async def get_current_employee(
    user: Annotated[User, Depends(current_user)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
) -> EmployeeRead:  # Не забудьте импортировать модель Employee
    employee = await employee_repo.get_by_user_id(user.id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль сотрудника для данного пользователя не найден",
        )
    return employee

# 2. Зависимость для проверки прав админа/мастера
async def require_admin_or_master(
    employee: Annotated[Employee, Depends(get_current_employee)],
) -> Employee:
    if employee.role not in [Role.admin, Role.master]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав доступа к этому ресурсу",
        )
    return employee