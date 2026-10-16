from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from starlette.requests import Request

from app.api.api_v1.dependencies import require_admin_or_master
from app.api.api_v1.fastapi_users import fastapi_users
from app.core import settings
from app.core.auth.user_manager_helper import get_user_manager_helper, UserManagerHelper
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.qr_data import QRData
from app.database.schemas.user import UserUpdate, UserRead

router = APIRouter(
    prefix=settings.api.v1.users,
    tags=["Users"],
)

router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))


@router.post(
    "/get-qr-code",
    response_model=QRData,
    status_code=status.HTTP_200_OK,
)
async def get_qr_code_for_employee(
    employee_id: int,
    request: Request,
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user_manager: Annotated[UserManagerHelper, Depends(get_user_manager_helper)],
    employee: Annotated[EmployeeRead, Depends(require_admin_or_master)],
) -> QRData:
    try:
        target_employee = await employee_repo.get_by_id(employee_id)
        if not target_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сотрудник не найден",
            )

        target_user = await user_manager.get_user_by_id(user_id=target_employee.user_id)

        await user_manager.forgot_password(user=target_user, request=request)

        qr_data = getattr(request.state, "qr_data", None)
        if not qr_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось сгенерировать данные для QR-кода",
            )

        return QRData(**qr_data)

    except HTTPException as exc:
        raise exc
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла внутренняя ошибка при генерации QR-кода",
        )
