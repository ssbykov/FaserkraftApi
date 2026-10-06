import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from typing import Annotated, AsyncGenerator, Type

from fastapi import Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core import settings
from app.database.models import BaseWithId
from app.database.schemas import (
    BaseSchema,
)


from sqlalchemy.pool import NullPool


class DbHelper:
    def __init__(self, url: str, echo: bool = False, use_null_pool: bool = False):
        kwargs: dict = {"url": url, "echo": echo}
        if use_null_pool:
            kwargs["poolclass"] = NullPool
        self.engine = create_async_engine(**kwargs)
        self.async_session = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session() as session:
            yield session

    @staticmethod
    async def _init_model(
        session: AsyncSession,
        model_class: Type[BaseWithId],
        schema_class: Type[BaseSchema],
    ) -> None:
        result = await session.execute(select(func.count()).select_from(model_class))
        count = result.scalar()
        if count == 0:
            for el in model_class.init_data:
                el_schema = schema_class(**el)
                session.add(el_schema.to_orm())

    async def synch_backups(self, session: AsyncSession | None = None) -> None:
        from .crud.backup_db import BackupDbRepository

        if session is not None:
            await BackupDbRepository(session).synchronize()
            return
        async for s in self.get_session():
            await BackupDbRepository(s).synchronize()


db_helper = DbHelper(url=str(settings.db.url), echo=settings.db.echo)
worker_db_helper = DbHelper(
    url=str(settings.db.url), echo=settings.db.echo, use_null_pool=True
)
SessionDep = Annotated[AsyncSession, Depends(db_helper.get_session)]