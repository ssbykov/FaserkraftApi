from app.database import BaseSchema


class PackagingBase(BaseSchema):
    serial_number: str

    model_config = {"from_attributes": True}

class PackagingCreate(PackagingBase):
    pass

class PackagingRead(PackagingBase):
    id: int
