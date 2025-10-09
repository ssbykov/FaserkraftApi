from fastapi import APIRouter

from app.core import settings
from app.database.schemas.user import UserUpdate, UserRead
from .fastapi_users import fastapi_users

router = APIRouter(
    prefix=settings.api.v1.users,
    tags=["Users"],
)

router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))
