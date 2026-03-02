from pydantic import BaseModel


class QRData(BaseModel):
    action: str
    id: int
    token: str
