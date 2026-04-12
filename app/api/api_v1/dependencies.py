from typing import Annotated

from fastapi import HTTPException, Depends
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.models import User
from app.database.models.employee import Role
from app.database.schemas.employee import EmployeeRead


async def get_current_employee(
    user: Annotated[User, Depends(current_user)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
) -> EmployeeRead:
    employee = await employee_repo.get_by_user_id(user.id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль сотрудника для данного пользователя не найден",
        )
    return employee


async def require_admin_or_master(
    # Здесь тоже указываем EmployeeRead, так как get_current_employee возвращает его
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> EmployeeRead:
    if employee.role not in [Role.admin, Role.master]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав доступа к этому ресурсу",
        )
    return employee
