import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import lazyload

from app.database import db_helper
from app.database.models import (
    Device,
    DeviceInvitation,
    Employee,
    MobileSession,
    User,
)


# Временная политика до добавления настроек и продления сессий.
MOBILE_SESSION_LIFETIME = timedelta(hours=12)

MAX_INVITATION_TOKEN_LENGTH = 512


class MobileRegistrationError(Exception):
    """Ожидаемая ошибка регистрации мобильного устройства."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class MobileRegistrationResult:
    access_token: str
    expires_at: datetime
    user_email: str
    employee_name: str
    employee_role: str
    device_id: str
    model: str
    manufacturer: str


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def register_mobile_device(
    *,
    invitation_token: str,
    device_id: str,
    model: str,
    manufacturer: str,
) -> MobileRegistrationResult:
    """
    Обменивает приглашение на устройство и мобильную сессию.

    Все изменения выполняются в одной транзакции.
    Порядок блокировок:
    сотрудник -> приглашение -> пользователь -> старое устройство.
    """
    if (
        not isinstance(invitation_token, str)
        or not invitation_token
        or len(invitation_token) > MAX_INVITATION_TOKEN_LENGTH
    ):
        raise MobileRegistrationError(
            "INVALID_DEVICE_INVITATION"
        )

    device_fields = (device_id, model, manufacturer)

    if any(
        not isinstance(value, str) or not value.strip()
        for value in device_fields
    ):
        raise MobileRegistrationError("INVALID_DEVICE_DATA")

    invitation_hash = hash_token(invitation_token)

    async with db_helper.async_session() as session:
        try:
            async with session.begin():
                # Сначала получаем только ID получателя.
                # Приглашение пока не блокируем.
                employee_id = await session.scalar(
                    select(DeviceInvitation.employee_id).where(
                        DeviceInvitation.token_hash == invitation_hash,
                    )
                )

                if employee_id is None:
                    raise MobileRegistrationError(
                        "INVALID_DEVICE_INVITATION"
                    )

                # Все регистрации одного сотрудника выполняются
                # последовательно через блокировку его строки.
                employee = await session.scalar(
                    select(Employee)
                    .options(lazyload("*"))
                    .where(Employee.id == employee_id)
                    .with_for_update(of=Employee)
                )

                if employee is None or employee.user_id is None:
                    raise MobileRegistrationError(
                        "INVALID_DEVICE_INVITATION"
                    )

                # Повторно проверяем приглашение после получения
                # блокировки сотрудника.
                invitation = await session.scalar(
                    select(DeviceInvitation)
                    .where(
                        DeviceInvitation.token_hash == invitation_hash,
                        DeviceInvitation.employee_id == employee.id,
                    )
                    .with_for_update(of=DeviceInvitation)
                )

                if invitation is None:
                    raise MobileRegistrationError(
                        "INVALID_DEVICE_INVITATION"
                    )

                user = await session.scalar(
                    select(User)
                    .options(lazyload("*"))
                    .where(User.id == employee.user_id)
                    .with_for_update(of=User)
                )

                if (
                    user is None
                    or not user.is_active
                    or not user.is_verified
                ):
                    raise MobileRegistrationError(
                        "USER_NOT_ALLOWED"
                    )

                old_device: Device | None = None

                if employee.device_id is not None:
                    old_device = await session.scalar(
                        select(Device)
                        .options(lazyload("*"))
                        .where(Device.id == employee.device_id)
                        .with_for_update(of=Device)
                    )

                    if old_device is None:
                        raise RuntimeError(
                            "Employee refers to a missing device"
                        )

                # Проверяем срок после ожидания всех основных
                # блокировок, используя текущее время PostgreSQL.
                now: datetime = (
                    await session.execute(
                        select(func.clock_timestamp())
                    )
                ).scalar_one()

                used_at: datetime | None = invitation.used_at
                revoked_at: datetime | None = invitation.revoked_at
                expires_at: datetime = invitation.expires_at

                if used_at is not None:
                    raise MobileRegistrationError("INVALID_DEVICE_INVITATION")

                if revoked_at is not None:
                    raise MobileRegistrationError("INVALID_DEVICE_INVITATION")

                if expires_at <= now:
                    raise MobileRegistrationError("INVALID_DEVICE_INVITATION")

                existing_device_id = await session.scalar(
                    select(Device.id).where(
                        Device.device_id == device_id,
                    )
                )

                if existing_device_id is not None:
                    raise MobileRegistrationError(
                        "DEVICE_ALREADY_REGISTERED"
                    )

                device = Device(
                    device_id=device_id,
                    model=model,
                    manufacturer=manufacturer,
                    is_active=True,
                )
                session.add(device)

                # Получаем внутренний devices.id.
                # Конкурентное создание такого же device_id
                # дополнительно защищено UNIQUE в БД.
                await session.flush()

                if old_device is not None:
                    old_device.is_active = False

                    await session.execute(
                        update(MobileSession)
                        .where(
                            MobileSession.device_id == old_device.id,
                            MobileSession.revoked_at.is_(None),
                        )
                        .values(revoked_at=now)
                        .execution_options(
                            synchronize_session=False,
                        )
                    )

                employee.device_id = device.id
                invitation.used_at = now

                # Другие неиспользованные приглашения сотрудника
                # больше не должны заменять только что
                # зарегистрированное устройство.
                await session.execute(
                    update(DeviceInvitation)
                    .where(
                        DeviceInvitation.employee_id == employee.id,
                        DeviceInvitation.id != invitation.id,
                        DeviceInvitation.used_at.is_(None),
                        DeviceInvitation.revoked_at.is_(None),
                    )
                    .values(revoked_at=now)
                    .execution_options(
                        synchronize_session=False,
                    )
                )

                access_token = secrets.token_urlsafe(32)
                expires_at = now + MOBILE_SESSION_LIFETIME

                mobile_session = MobileSession(
                    token_hash=hash_token(access_token),
                    user_id=user.id,
                    device_id=device.id,
                    expires_at=expires_at,
                )
                session.add(mobile_session)

                await session.flush()

                result = MobileRegistrationResult(
                    access_token=access_token,
                    expires_at=expires_at,
                    user_email=user.email,
                    employee_name=employee.name,
                    employee_role=employee.role.value,
                    device_id=device.device_id,
                    model=device.model,
                    manufacturer=device.manufacturer,
                )

            # Транзакция уже успешно зафиксирована.
            return result

        except IntegrityError as exc:
            # Ошибка могла возникнуть не только из-за device_id,
            # поэтому не выдаём любой IntegrityError за дубликат.
            raise MobileRegistrationError(
                "REGISTRATION_CONFLICT"
            ) from exc
