import secrets
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select

from app.database import db_helper
from app.database.models import Device, Employee, MobileSession, User
from app.services.mobile_registration import ACCESS_LIFETIME, hash_token

MAX_REFRESH_TOKEN_LENGTH = 512


class MobileRefreshError(Exception):
    """Refresh-токен недействителен или устройство/пользователь не допущены."""


@dataclass(frozen=True, slots=True)
class MobileRefreshResult:
    access_token: str
    refresh_token: str
    expires_at: datetime


async def refresh_mobile_session(*, refresh_token: str) -> MobileRefreshResult:
    if (
        not isinstance(refresh_token, str)
        or not refresh_token
        or len(refresh_token) > MAX_REFRESH_TOKEN_LENGTH
    ):
        raise MobileRefreshError

    presented_hash = hash_token(refresh_token)

    async with db_helper.async_session() as session:
        async with session.begin():
            ms = await session.scalar(
                select(MobileSession)
                .where(
                    or_(
                        MobileSession.refresh_token_hash == presented_hash,
                        MobileSession.prev_refresh_token_hash
                        == presented_hash,
                    )
                )
                .with_for_update()
            )

            if ms is None or ms.revoked_at is not None:
                raise MobileRefreshError

            allowed = await session.execute(
                select(User.id)
                .join(Employee, Employee.user_id == User.id)
                .join(Device, Device.id == Employee.device_id)
                .where(
                    User.id == ms.user_id,
                    User.is_active.is_(True),
                    User.is_verified.is_(True),
                    Device.id == ms.device_id,
                    Device.is_active.is_(True),
                )
            )

            if allowed.first() is None:
                raise MobileRefreshError

            now: datetime = (
                await session.execute(select(func.clock_timestamp()))
            ).scalar_one()

            access_token = secrets.token_urlsafe(32)
            new_refresh = secrets.token_urlsafe(48)

            ms.prev_refresh_token_hash = ms.refresh_token_hash
            ms.refresh_token_hash = hash_token(new_refresh)
            ms.token_hash = hash_token(access_token)
            ms.expires_at = now + ACCESS_LIFETIME

            return MobileRefreshResult(
                access_token=access_token,
                refresh_token=new_refresh,
                expires_at=ms.expires_at,
            )