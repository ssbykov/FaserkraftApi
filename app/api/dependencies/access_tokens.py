from typing import TYPE_CHECKING, Any

from fastapi import Depends

from app.database import db_helper
from app.database.models import AccessToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_access_token_db(
    session: "AsyncSession" = Depends(db_helper.get_session),
) -> Any:
    yield AccessToken.get_db(session)
