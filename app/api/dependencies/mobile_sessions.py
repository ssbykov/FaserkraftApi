import hashlib
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.database import SessionDep
from app.database.models import (
    Device,
    Employee,
    MobileSession,
    User,
)
from app.database.schemas.employee import EmployeeRead
from app.database.models.employee import Role

mobile_bearer = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="INVALID_MOBILE_SESSION",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_mobile_employee(
    session: SessionDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(mobile_bearer),
    ],
) -> EmployeeRead:
    if credentials is None:
        raise unauthorized()

    if credentials.scheme.lower() != "bearer":
        raise unauthorized()

    token = credentials.credentials

    # Ограничение для предлагаемого формата случайных токенов.
    if not token or len(token) > 512:
        raise unauthorized()

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    now = datetime.now(timezone.utc)

    stmt = (
        select(Employee)
        .join(
            User,
            User.id == Employee.user_id,
        )
        .join(
            MobileSession,
            MobileSession.user_id == User.id,
        )
        .join(
            Device,
            Device.id == MobileSession.device_id,
        )
        .where(
            MobileSession.token_hash == token_hash,
            MobileSession.revoked_at.is_(None),
            MobileSession.expires_at > now,
            User.is_active.is_(True),
            User.is_verified.is_(True),
            Device.is_active.is_(True),
            Employee.device_id == Device.id,
        )
    )

    employee = await session.scalar(stmt)

    if employee is None:
        raise unauthorized()

    return EmployeeRead.model_validate(employee)

async def require_mobile_admin_or_master(
    employee: Annotated[
        EmployeeRead,
        Depends(get_current_mobile_employee),
    ],
) -> EmployeeRead:
    if employee.role not in (Role.admin, Role.master):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав доступа к этому ресурсу",
        )

    return employee