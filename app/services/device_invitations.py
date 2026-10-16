import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import lazyload

from app.database import db_helper
from app.database.models import DeviceInvitation, Employee, User
from app.database.models.employee import Role


DEVICE_INVITATION_LIFETIME = timedelta(minutes=10)


class DeviceInvitationError(Exception):
    """Ожидаемая ошибка выдачи приглашения устройства."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class DeviceInvitationResult:
    invitation_id: int
    employee_id: int
    invitation_token: str
    expires_at: datetime


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_device_invitation(
    *,
    actor_user_id: int,
    employee_id: int,
) -> DeviceInvitationResult:
    """
    Выдаёт новое приглашение и отзывает предыдущие.

    actor_user_id должен приходить из серверной аутентификации,
    а не из тела клиентского запроса.

    Сервис владеет собственной сессией и транзакцией.
    """
    if actor_user_id <= 0:
        raise DeviceInvitationError("INVITATION_FORBIDDEN")

    if employee_id <= 0:
        raise DeviceInvitationError("EMPLOYEE_NOT_FOUND")

    async with db_helper.async_session() as session:
        async with session.begin():
            actor = await session.scalar(
                select(User)
                .options(lazyload("*"))
                .where(User.id == actor_user_id)
            )

            if (
                actor is None
                or not actor.is_active
                or not actor.is_verified
            ):
                raise DeviceInvitationError(
                    "INVITATION_FORBIDDEN"
                )

            if not actor.is_superuser:
                actor_role = await session.scalar(
                    select(Employee.role).where(
                        Employee.user_id == actor.id,
                    )
                )

                if actor_role not in (Role.admin, Role.master):
                    raise DeviceInvitationError(
                        "INVITATION_FORBIDDEN"
                    )

            # Тот же первый объект блокировки, что и в
            # register_mobile_device: сотрудник-получатель.
            employee = await session.scalar(
                select(Employee)
                .options(lazyload("*"))
                .where(Employee.id == employee_id)
                .with_for_update(of=Employee)
            )

            if employee is None:
                raise DeviceInvitationError(
                    "EMPLOYEE_NOT_FOUND"
                )

            if employee.user_id is None:
                raise DeviceInvitationError(
                    "EMPLOYEE_HAS_NO_USER"
                )

            recipient = await session.scalar(
                select(User)
                .options(lazyload("*"))
                .where(User.id == employee.user_id)
                .with_for_update(of=User)
                .execution_options(populate_existing=True)
            )

            if (
                recipient is None
                or not recipient.is_active
                or not recipient.is_verified
            ):
                raise DeviceInvitationError(
                    "RECIPIENT_NOT_ALLOWED"
                )

            now: datetime = (
                await session.execute(
                    select(func.clock_timestamp())
                )
            ).scalar_one()

            # Получатель заблокирован: параллельная выдача
            # или регистрация через согласованный сервис ждёт.
            await session.execute(
                update(DeviceInvitation)
                .where(
                    DeviceInvitation.employee_id == employee.id,
                    DeviceInvitation.used_at.is_(None),
                    DeviceInvitation.revoked_at.is_(None),
                )
                .values(revoked_at=now)
                .execution_options(
                    synchronize_session=False,
                )
            )

            invitation_token = secrets.token_urlsafe(32)
            expires_at = now + DEVICE_INVITATION_LIFETIME

            invitation = DeviceInvitation(
                token_hash=hash_invitation_token(
                    invitation_token
                ),
                employee_id=employee.id,
                created_by_user_id=actor.id,
                expires_at=expires_at,
            )

            session.add(invitation)
            await session.flush()

            result = DeviceInvitationResult(
                invitation_id=invitation.id,
                employee_id=employee.id,
                invitation_token=invitation_token,
                expires_at=expires_at,
            )

        # Возвращаем исходный токен только после commit.
        return result