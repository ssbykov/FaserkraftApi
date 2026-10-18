from sqlalchemy import func, select, update

from app.database import db_helper
from app.database.models import Device, Employee, MobileSession
from app.services.mobile_registration import hash_token


async def revoke_mobile_device(*, access_token: str) -> None:
    token_hash = hash_token(access_token)

    async with db_helper.async_session() as session:
        async with session.begin():
            ms = await session.scalar(
                select(MobileSession)
                .where(MobileSession.token_hash == token_hash)
                .with_for_update()
            )
            if ms is None:
                return

            now = (await session.execute(select(func.clock_timestamp()))).scalar_one()

            await session.execute(
                update(MobileSession)
                .where(
                    MobileSession.device_id == ms.device_id,
                    MobileSession.revoked_at.is_(None),
                )
                .values(revoked_at=now)
                .execution_options(synchronize_session=False)
            )
            await session.execute(
                update(Device)
                .where(Device.id == ms.device_id)
                .values(is_active=False)
                .execution_options(synchronize_session=False)
            )
            await session.execute(
                update(Employee)
                .where(Employee.device_id == ms.device_id)
                .values(device_id=None)
                .execution_options(synchronize_session=False)
            )