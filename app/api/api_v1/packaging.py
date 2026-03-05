from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.core import settings
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.crud.packaging import get_packaging_repo, PackagingRepository
from app.database.models import User, Packaging
from app.database.schemas.packaging import PackagingRead, PackagingCreate, PackagingCreateWithProducts

router = APIRouter(
    tags=["Packaging"],
    prefix=settings.api.v1.packaging,
)


@router.post(
    "",
    response_model=PackagingRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_packaging(
    data: PackagingCreateWithProducts,
    repo: Annotated[PackagingRepository, Depends(get_packaging_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
) -> Packaging:
    try:
        employee = await employee_repo.get_by_user_id(user.id)
        packaging = PackagingCreate(
            serial_number=data.serial_number,
            performed_at=data.performed_at,
            performed_by_id=employee.id,
        )
        packaging = await repo.create_packaging(
            packaging_in=packaging,
            products=data.products
        )
        return packaging
    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при создании упаковки",
        )

@router.get(
    "/{serial_number}",
    response_model=PackagingRead,
    status_code=status.HTTP_200_OK,
)
async def get_packaging(
    serial_number: str,
    repo: Annotated[PackagingRepository, Depends(get_packaging_repo)],
    user: Annotated[User, Depends(current_user)],
) -> PackagingRead:
    try:
        packaging = await repo.get(serial_number=serial_number)
        return PackagingRead.model_validate(packaging)
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении продукта",
        )