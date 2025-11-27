from app.database import SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import Device
from app.database.schemas.device import DeviceCreate


def get_device_repo(session: SessionDep) -> "DeviceRepository":
    return DeviceRepository(session)


class DeviceRepository(GetBackNextIdMixin[Device]):
    model = Device

    async def create_device(self, device_in: DeviceCreate) -> Device:
        device = device_in.to_orm()
        self.session.add(device)

        try:
            await self.session.flush()
            await self.session.commit()
        except Exception as e:
            print(e)
            await self.session.rollback()
            raise

        await self.session.refresh(device)
        return device
