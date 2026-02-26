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

router = APIRouter(
    tags=["Employees"],
    prefix=settings.api.v1.employees,
)
router.include_router(
    router,
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
