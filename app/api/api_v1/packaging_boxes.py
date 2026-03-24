from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, HTTPException, Depends
from starlette import status

from app.api.api_v1.fastapi_users import current_user
from app.core import settings
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.crud.packaging_box import get_packaging_repo, PackagingRepository
from app.database.models import User, Packaging
from app.database.schemas.packaging_box import (
    PackagingRead,
    PackagingCreate,
    PackagingCreateWithProducts,
)
from database.models.employee import Role

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
            performed_by_id=employee.id,
        )
        packaging = await repo.create_packaging(
            packaging_in=packaging, products=data.products
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
    "/by_serial/{serial_number}",
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
            detail="Произошла внутренняя ошибка при получении упаковки",
        )


@router.post(
    "/shipment",
    status_code=status.HTTP_200_OK,
)
async def set_packaging_shipment(
    packaging_ids: List[int],
    repo: Annotated[PackagingRepository, Depends(get_packaging_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user: Annotated[User, Depends(current_user)],
):
    try:
        employee = await employee_repo.get_by_user_id(user.id)

        if employee.role not in [Role.admin, Role.master]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данная операция недоступна",
            )

        await repo.set_shipment_for_packaging(
            packaging_ids=packaging_ids,
            shipment_by_id=employee.id,
            shipment_at=datetime.now(),
        )

        return {"updated_ids": packaging_ids}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при установке отгрузки",
        )


@router.get(
    "/get_all_in_storage",
    response_model=list[PackagingRead],
    status_code=status.HTTP_200_OK,
)
async def get_all_in_storage(
    repo: Annotated[PackagingRepository, Depends(get_packaging_repo)],
    user: Annotated[User, Depends(current_user)],
) -> list[PackagingRead]:
    try:
        packaging_boxes = await repo.get_all_without_shipment()
        return [PackagingRead.model_validate(p) for p in packaging_boxes]
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        # внутренняя ошибка без лишних деталей наружу
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при получении списка упаковок",
        )


@router.delete(
    "/{serial_number}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_packaging(
    serial_number: str,
    repo: Annotated[PackagingRepository, Depends(get_packaging_repo)],
    user: Annotated[User, Depends(current_user)],
) -> None:
    try:
        await repo.delete(serial_number=serial_number)
        return
    except HTTPException as exc:
        # пробрасываем 404 и другие осознанные HTTP-ошибки
        raise exc
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Произошла внутренняя ошибка при удалении упаковки",
        )
