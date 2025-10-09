from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends
from fastapi_users.authentication.strategy.db import (
    DatabaseStrategy,
)

from app.api.dependencies.access_tokens import get_access_token_db
from app.core import settings

if TYPE_CHECKING:
    from app.database import AccessToken
    from fastapi_users.authentication.strategy import (
        AccessTokenDatabase,
    )


def get_database_strategy(
    access_token_db: Annotated[
        "AccessTokenDatabase[AccessToken]", Depends(get_access_token_db)
    ],
) -> Any:
    return DatabaseStrategy(
        database=access_token_db,
        lifetime_seconds=settings.access_token.lifetime_seconds,
    )
