from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import Process
from app.database.crud.mixines import GetBackNextIdMixin


class ProcessRepository(GetBackNextIdMixin[Process]):
    model = Process

    async def get(self, process_id: int) -> Process:
        stmt = (
            select(self.model)
            .options(selectinload(self.model.steps))  # stages — имя relationship поля
            .where(self.model.id == process_id)
        )
        process = await self.session.scalar(stmt)
        if process:
            return process
        raise HTTPException(
            status_code=404, detail=f"Процесс с id {process_id} не найден"
        )
