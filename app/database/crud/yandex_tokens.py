from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import YandexToken


class YandexTokensRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tokens(self) -> tuple[str, str, datetime]:
        stmt = select(YandexToken).filter_by(id="main")
        result = await self.session.execute(stmt)
        token = result.scalar_one_or_none()
        if not token:
            raise Exception("Токены не найдены")
        return token.access_token, token.refresh_token, token.expires_at

    async def save_tokens(
        self, access_token: str, refresh_token: str, expires_at: datetime
    ):
        token = YandexToken(
            id="main",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(token)
        await self.session.commit()
