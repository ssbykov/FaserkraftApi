import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.api_v1.fastapi_users import current_user
from app.api.dependencies.mobile_sessions import (
    get_current_mobile_employee,
    require_mobile_admin_or_master,
)
from app.core import settings
from app.database import SessionDep
from app.database.models import Employee, User
from app.database.schemas.employee import EmployeeRead
from app.database.schemas.mobile import (
    MobileDeviceRegistered,
    MobileInvitationIssue,
    MobileInvitationIssued,
    MobileRefresh,
    MobileRegisterDevice,
    MobileTokens,
)
from app.services.device_invitations import (
    DeviceInvitationError,
    DeviceInvitationResult,
    issue_device_invitation,
)
from app.services.mobile_refresh import (
    MobileRefreshError,
    refresh_mobile_session,
)
from app.services.mobile_registration import (
    MobileRegistrationError,
    MobileRegistrationResult,
    register_mobile_device,
)

router = APIRouter(
    tags=["MobileAuth"],
    prefix=settings.api.v1.mobile,
)


def _map_invitation_error(exc: DeviceInvitationError) -> HTTPException:
    if exc.code == "INVITATION_FORBIDDEN":
        status_code = status.HTTP_403_FORBIDDEN
        detail = "INVITATION_FORBIDDEN"
    elif exc.code == "EMPLOYEE_NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
        detail = "EMPLOYEE_NOT_FOUND"
    elif exc.code == "EMPLOYEE_HAS_NO_USER":
        status_code = status.HTTP_409_CONFLICT
        detail = "EMPLOYEE_HAS_NO_USER"
    elif exc.code == "RECIPIENT_NOT_ALLOWED":
        status_code = status.HTTP_409_CONFLICT
        detail = "RECIPIENT_NOT_ALLOWED"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = "INTERNAL_SERVER_ERROR"

    return HTTPException(status_code=status_code, detail=detail)


def _map_registration_error(exc: MobileRegistrationError) -> HTTPException:
    if exc.code == "INVALID_DEVICE_INVITATION":
        status_code = status.HTTP_400_BAD_REQUEST
        detail = "INVALID_DEVICE_INVITATION"
    elif exc.code == "DEVICE_ALREADY_REGISTERED":
        status_code = status.HTTP_409_CONFLICT
        detail = "DEVICE_ALREADY_REGISTERED"
    elif exc.code == "USER_NOT_ALLOWED":
        status_code = status.HTTP_403_FORBIDDEN
        detail = "USER_NOT_ALLOWED"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = "INTERNAL_SERVER_ERROR"

    return HTTPException(status_code=status_code, detail=detail)


def _build_invitation_response(
    result: DeviceInvitationResult,
) -> MobileInvitationIssued:
    qr_payload = json.dumps(
        {
            "employee_id": result.employee_id,
            "invitation_token": result.invitation_token,
        },
        separators=(",", ":"),
    )
    return MobileInvitationIssued(
        invitation_id=result.invitation_id,
        employee_id=result.employee_id,
        invitation_token=result.invitation_token,
        expires_at=result.expires_at,
        qr_payload=qr_payload,
    )


@router.post(
    "/invitations",
    response_model=MobileInvitationIssued,
    status_code=status.HTTP_201_CREATED,
)
async def create_device_invitation(
    payload: MobileInvitationIssue,
    current: Annotated[User, Depends(current_user)],
) -> MobileInvitationIssued:
    try:
        result = await issue_device_invitation(
            actor_user_id=current.id,
            employee_id=payload.employee_id,
        )
    except DeviceInvitationError as exc:
        raise _map_invitation_error(exc) from exc

    return _build_invitation_response(result)


@router.post(
    "/invitations/by-mobile",
    response_model=MobileInvitationIssued,
    status_code=status.HTTP_201_CREATED,
)
async def create_device_invitation_by_mobile(
    payload: MobileInvitationIssue,
    session: SessionDep,
    employee: Annotated[EmployeeRead, Depends(require_mobile_admin_or_master)],
) -> MobileInvitationIssued:
    actor_user_id = await session.scalar(
        select(Employee.user_id).where(Employee.id == employee.id)
    )
    if actor_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INVITATION_FORBIDDEN",
        )

    try:
        result = await issue_device_invitation(
            actor_user_id=actor_user_id,
            employee_id=payload.employee_id,
        )
    except DeviceInvitationError as exc:
        raise _map_invitation_error(exc) from exc

    return _build_invitation_response(result)


@router.post(
    "/register-device",
    response_model=MobileDeviceRegistered,
    status_code=status.HTTP_201_CREATED,
)
async def register_device_from_invitation(
    payload: MobileRegisterDevice,
) -> MobileDeviceRegistered:
    try:
        result: MobileRegistrationResult = await register_mobile_device(
            invitation_token=payload.invitation_token,
            device_id=payload.device_id.strip(),
            model=payload.model.strip(),
            manufacturer=payload.manufacturer.strip(),
        )
    except MobileRegistrationError as exc:
        raise _map_registration_error(exc) from exc

    return MobileDeviceRegistered(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_at=result.expires_at,
        user_email=result.user_email,
        employee_name=result.employee_name,
        employee_role=result.employee_role,
        device_id=result.device_id,
        model=result.model,
        manufacturer=result.manufacturer,
    )


@router.post(
    "/refresh",
    response_model=MobileTokens,
)
async def refresh_mobile_tokens(payload: MobileRefresh) -> MobileTokens:
    try:
        result = await refresh_mobile_session(
            refresh_token=payload.refresh_token,
        )
    except MobileRefreshError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_REFRESH_TOKEN",
        ) from exc

    return MobileTokens(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_at=result.expires_at,
    )


@router.get(
    "/me",
    response_model=EmployeeRead,
)
async def read_current_mobile_employee(
    employee: Annotated[
        EmployeeRead,
        Depends(get_current_mobile_employee),
    ],
) -> EmployeeRead:
    return employee