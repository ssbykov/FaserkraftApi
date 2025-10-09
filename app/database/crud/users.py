from sqlalchemy import select

from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import User


class UsersRepository(GetBackNextIdMixin[User]):
    model = User

    async def get_user_id(self, email: str) -> int:
        result = await self.session.execute(
            select(self.model.id).where(self.model.email == email)  # type: ignore[arg-type]
        )
        return result.scalar_one()
