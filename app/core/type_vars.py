from typing import TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from app.database import BaseWithId

T = TypeVar("T", bound="BaseWithId")
