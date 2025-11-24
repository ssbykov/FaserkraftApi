from app.database import SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import Device
from app.database.schemas.device_schema import DeviceCreate


def get_product_repo(session: SessionDep) -> "DeviceRepository":
    return DeviceRepository(session)


class DeviceRepository(GetBackNextIdMixin[Device]):
    model = Device

    async def create_device(self, device_in: DeviceCreate):
        device = device_in.to_orm()
        self.session.add(device)
        await self.session.commit()
        await self.session.refresh(device)
        return device
