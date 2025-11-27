import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from starlette import status
from starlette.responses import JSONResponse

from app.api.api_v1.fastapi_users import fastapi_users
from app.core import settings
from app.database.crud.devices import DeviceRepository, get_device_repo
from app.database.crud.employees import EmployeeRepository, get_employee_repo
from app.database.schemas.device import DeviceRead, DeviceCreate, DeviceRegister
from app.database.schemas.user import UserUpdate, UserRead

router = APIRouter(
    prefix=settings.api.v1.users,
    tags=["Users"],
)

router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))


@router.post(
    "/",
    response_model=None,  # твоя схема ответа
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    device_in: DeviceRegister,
    device_repo: Annotated[DeviceRepository, Depends(get_device_repo)],
    employee_repo: Annotated[EmployeeRepository, Depends(get_employee_repo)],
) -> str:
    try:
        result = await register_device_logic(device_in, device_repo, employee_repo)
        if result:
            async with httpx.AsyncClient() as client:
                data = {"token": device_in.token, "password": device_in.password}
                resp = await client.post(
                    "http://localhost:8000/api/v1/auth/reset-password",
                    json=data,
                )

            return JSONResponse(
                status_code=resp.status_code,
                content=resp.json(),
            )
    except Exception as e:
        logging.error(e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal error"},
        )


async def register_device_logic(
    device_in: DeviceRegister,
    device_repo: DeviceRepository,
    employee_repo: EmployeeRepository,
):
    new_device = DeviceCreate(**device_in.model_dump())
    device = await device_repo.create_device(new_device)
    await employee_repo.attach_device(device_in.user_id, device)
    return DeviceRead.model_validate(device)
