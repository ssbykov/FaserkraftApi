from datetime import datetime

from pydantic import Field

from app.database import BaseSchema


class MobileInvitationIssue(BaseSchema):
    """
    Параметры выдачи приглашения устройства.

    ID инициатора не принимается из запроса:
    пользователя определяет серверная авторизация.
    """

    employee_id: int = Field(gt=0)


class MobileInvitationIssued(BaseSchema):
    """
    Результат выдачи приглашения.

    QR custom payload для Android будет сформирован
    на следующем этапе.
    """

    invitation_id: int
    employee_id: int
    invitation_token: str
    expires_at: datetime
    qr_payload: str


class MobileRegisterDevice(BaseSchema):
    """
    Обмен приглашения на мобильное устройство и сессию.

    Строковые поля нужны обработчику: передаваемые
    сервису значения он проверяет после обрезки пробелов.
    """

    invitation_token: str = Field(
        min_length=1,
        max_length=512,
    )
    device_id: str = Field(min_length=1, max_length=255)
    model: str = Field(min_length=1, max_length=255)
    manufacturer: str = Field(
        min_length=1,
        max_length=255,
    )


class MobileDeviceRegistered(BaseSchema):
    """Мобильная сессия и сведения о зарегистрированном устройстве."""

    access_token: str
    expires_at: datetime
    user_email: str
    employee_name: str
    employee_role: str
    device_id: str
    model: str
    manufacturer: str
