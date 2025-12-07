from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import Process, SessionDep, StepDefinition
from app.database.crud.mixines import GetBackNextIdMixin


def get_process_repo(session: SessionDep) -> "ProcessRepository":
    return ProcessRepository(session)


class ProcessRepository(GetBackNextIdMixin[Process]):
    model = Process

    async def copy_process(self, process_id: int) -> Process:
        stmt = (
            select(Process)
            .options(selectinload(Process.steps))
            .where(Process.id == process_id)
        )
        res = await self.session.execute(stmt)
        original: Process | None = res.scalars().first()

        if original is None:
            raise ValueError("Процесс с таким process_id не найден")

        # 2) создаём новый процесс
        new_process = Process(
            name=f"{original.name} (копия)",
            description=f"{original.description} (копия)",
        )
        self.session.add(new_process)
        await self.session.flush()  # нужен new_process.id

        # 3) копируем шаги (только FK и order)
        for step in original.steps:
            new_step = StepDefinition(
                process_id=new_process.id,
                template_id=step.template_id,
                order=step.order,
            )
            self.session.add(new_step)

        # 4) коммит
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(new_process)
        return new_process
