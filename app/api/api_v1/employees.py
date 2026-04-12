from typing import List, Annotated

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.dependencies import require_admin_or_master
from app.core import settings
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.schemas.employee import EmployeeRead

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
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> List[EmployeeRead]:
    try:
        employees = await repo.get_all()
        return [EmployeeRead.model_validate(e) for e in employees]

    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении списка сотрудников",
        )
