from typing import Optional

from pydantic import BaseModel


class AdminAuthResponse(BaseModel):
    is_ok: bool
    error: Optional[str] = None
    message: Optional[str] = None
