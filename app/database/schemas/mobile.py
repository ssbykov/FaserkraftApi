from datetime import datetime

from pydantic import Field

from app.database import BaseSchema


class MobileInvitationIssue(BaseSchema):
    """ID инициатора определяет серверная авторизация, не запрос."""

    employee_id: int = Field(gt=0)


class MobileInvitationIssued(BaseSchema):
    invitation_id: int
    employee_id: int
    invitation_token: str
    expires_at: datetime
    qr_payload: str


class MobileRegisterDevice(BaseSchema):
    invitation_token: str = Field(min_length=1, max_length=512)
    device_id: str = Field(min_length=1, max_length=255)
    model: str = Field(min_length=1, max_length=255)
    manufacturer: str = Field(min_length=1, max_length=255)


class MobileDeviceRegistered(BaseSchema):
    access_token: str
    refresh_token: str
    expires_at: datetime
    user_email: str
    employee_name: str
    employee_role: str
    device_id: str
    model: str
    manufacturer: str


class MobileRefresh(BaseSchema):
    refresh_token: str = Field(min_length=1, max_length=512)


class MobileTokens(BaseSchema):
    access_token: str
    refresh_token: str
    expires_at: datetime

class MobileLogoutResult(BaseSchema):
    ok: bool = True