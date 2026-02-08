import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi_users.exceptions import InvalidResetPasswordToken
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette import status
from starlette.requests import Request

from app.api.api_v1.fastapi_users import fastapi_users
from app.core import settings
from app.core.auth.user_manager_helper import get_user_manager_helper, UserManagerHelper
from app.database import Employee
from app.database.crud.devices import DeviceRepository, get_device_repo
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.schemas.device import (
    DeviceRead,
    DeviceCreate,
    DeviceRegister,
    DeviceResponse,
)
from app.database.schemas.user import UserUpdate, UserRead

router = APIRouter(
    prefix=settings.api.v1.users,
    tags=["Users"],
)

router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))


@router.post(
    "/new-device",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    device_in: DeviceRegister,
    device_repo: Annotated[DeviceRepository, Depends(get_device_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
    user_manager: Annotated[UserManagerHelper, Depends(get_user_manager_helper)],
    request: Request,
) -> DeviceResponse:
    user = await user_manager.get_user_by_id(user_id=device_in.user_id)

    # 1. Пользователь должен существовать, быть активным и верифицированным
    if user is None or not user.is_active or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INACTIVE_OR_UNVERIFIED_USER",
        )

    # 2. Для обычного пользователя — сброс пароля по токену
    if not user.is_superuser:
        try:
            await user_manager.reset_password(
                token=device_in.token,
                password=device_in.password,
                request=request,
            )
        except InvalidResetPasswordToken as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="INVALID_RESET_PASSWORD_TOKEN",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    # 3. Регистрация устройства и привязка к сотруднику
    employee = await register_device_logic(device_in, device_repo, employee_repo)

    # 4. Формируем ответ
    return DeviceResponse(
        user_email=employee.user.email,
        employee_name=employee.name,
        employee_role=employee.role,
        device_id=device_in.device_id,
        model=device_in.model,
        manufacturer=device_in.manufacturer,
    )


async def register_device_logic(
    device_in: DeviceRegister,
    device_repo: DeviceRepository,
    employee_repo: EmployeeRepository,
) -> Employee:
    try:
        new_device = DeviceCreate(**device_in.model_dump())

        # 1) создаём устройство
        try:
            device = await device_repo.create_device(new_device)
        except IntegrityError as exc:
            # предполагаем, что сработало уникальное ограничение по device_id
            logging.exception("IntegrityError on create_device: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Устройство с таким ID уже зарегистрировано",
            ) from exc

        # 2) проверяем, что репозиторий вернул корректное устройство
        try:
            DeviceRead.model_validate(device)
        except ValidationError as exc:
            logging.exception("Device validation error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Данные устройства в хранилище не соответствуют схеме",
            ) from exc

        # 3) привязываем устройство к сотруднику
        employee = await employee_repo.attach_device(device_in.user_id, device)
        if employee is None:
            # репозиторий просто вернул None, без исключений
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сотрудник не найден",
            )

        return employee

    except HTTPException:
        # уже сформированный ответ
        raise
    except Exception as exc:
        logging.exception("Error in register_device_logic: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка при регистрации устройства",
        ) from exc
