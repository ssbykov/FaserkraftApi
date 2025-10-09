import contextlib
from typing import TYPE_CHECKING, Callable, Any

from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.exceptions import UserNotExists
from starlette.requests import Request

from app.api.dependencies.access_tokens import get_access_token_db
from app.api.dependencies.user_manager import get_user_manager
from app.api.dependencies.users import get_user_db
from app.database import db_helper
from app.database.models import User
from app.database.schemas.user import UserCreate

get_async_session_context = contextlib.asynccontextmanager(db_helper.get_session)
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)
get_access_token_db_context = contextlib.asynccontextmanager(get_access_token_db)

if TYPE_CHECKING:
    from app.core.auth.user_manager import UserManager


def with_user_manager(func: Callable[..., Any]) -> Callable[..., Any]:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with get_async_session_context() as session:
            async with get_user_db_context(session) as user_db:
                async with get_user_manager_context(user_db) as user_manager:
                    # Передаем user_manager в целевой метод
                    result = await func(user_manager=user_manager, *args, **kwargs)
                    return result

    return wrapper


class UserManagerHelper:
    @staticmethod
    @with_user_manager
    async def create_user(
        user_manager: "UserManager",
        user_create: UserCreate,
    ) -> User:
        user = await user_manager.create(
            user_create=user_create,
            safe=False,
        )
        return user

    @staticmethod
    @with_user_manager
    async def get_user_by_email(
        user_manager: "UserManager",
        user_email: str,
    ) -> User | None:
        try:
            return await user_manager.get_by_email(user_email)
        except UserNotExists:
            return None

    @staticmethod
    @with_user_manager
    async def get_user_by_id(
        user_manager: "UserManager",
        user_id: int,
    ) -> User:
        return await user_manager.get(id=user_id)

    @staticmethod
    @with_user_manager
    async def get_user(
        user_manager: "UserManager",
        credentials: OAuth2PasswordRequestForm,
    ) -> User | None:
        user = await user_manager.authenticate(credentials)
        if user and user.is_active and user.is_verified:
            return user
        return None

    @staticmethod
    @with_user_manager
    async def request_verify(
        user_manager: "UserManager",
        user: User,
    ) -> None:
        await user_manager.request_verify(user=user)

    @staticmethod
    @with_user_manager
    async def verify(
        user_manager: "UserManager",
        token: str,
    ) -> User:
        return await user_manager.verify(token=token)

    @staticmethod
    @with_user_manager
    async def forgot_password(
        user_manager: "UserManager",
        user: User,
        request: Request,
    ) -> None:
        await user_manager.forgot_password(user=user, request=request)
