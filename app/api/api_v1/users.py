import logging
from typing import Annotated

from fastapi import APIRouter, Depends
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
    try:

        await user_manager.reset_password(
            token=device_in.token,
            password=device_in.password,
            request=request,
        )

        employee = await register_device_logic(device_in, device_repo, employee_repo)
        return DeviceResponse(
            user_email=employee.user.email,
            employee_name=employee.name,
            device_id=device_in.device_id,
            model=device_in.model,
            manufacturer=device_in.manufacturer,
        )
    except Exception as e:
        logging.error(e)


async def register_device_logic(
    device_in: DeviceRegister,
    device_repo: DeviceRepository,
    employee_repo: EmployeeRepository,
) -> Employee:
    new_device = DeviceCreate(**device_in.model_dump())
    device = await device_repo.create_device(new_device)
    DeviceRead.model_validate(device)
    employee = await employee_repo.attach_device(device_in.user_id, device)
    return employee
