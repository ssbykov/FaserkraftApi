import contextlib
from datetime import datetime, timedelta, timezone
from typing import Callable, Any, TYPE_CHECKING

from app.api.dependencies.access_tokens import get_access_token_db
from app.api.dependencies.backend import authentication_backend
from app.core import settings
from app.core.auth.singleton import singleton
from app.database import db_helper

if TYPE_CHECKING:
    from app.database.models import User

get_async_session_context = contextlib.asynccontextmanager(db_helper.get_session)
get_access_token_db_context = contextlib.asynccontextmanager(get_access_token_db)


def with_token_db(func: Callable[..., Any]) -> Callable[..., Any]:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with get_async_session_context() as session:
            async with get_access_token_db_context(session) as token_db:
                result = await func(token_db=token_db, *args, **kwargs)
                return result

    return wrapper


@singleton
class AccessTokensHelper:
    def __init__(self) -> None:
        self.authentication_backend = authentication_backend

    @staticmethod
    async def check_access_token(
        token: Any,
    ) -> bool:
        if hasattr(token, "created_at"):
            return bool(
                token.created_at
                + timedelta(seconds=settings.access_token.lifetime_seconds)
                > datetime.now(tz=timezone.utc)
            )
        return False

    @staticmethod
    @with_token_db
    async def get_access_token(
        token: str,
        token_db: Any,
    ) -> Any:
        return await token_db.get_by_token(token=token)

    @with_token_db
    async def destroy_token(
        self,
        token: str,
        user: "User",
        token_db: Any,
    ) -> None:
        strategy = self.authentication_backend.get_strategy(token_db)
        await strategy.destroy_token(token=token, user=user)  # type: ignore

    @with_token_db
    async def write_token(
        self,
        user: "User",
        token_db: Any,
    ) -> str | None:
        strategy = self.authentication_backend.get_strategy(token_db)
        if hasattr(strategy, "write_token"):
            return await strategy.write_token(user)
        raise TypeError("Returned strategy does not have a write_token method.")
