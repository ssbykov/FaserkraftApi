from pathlib import Path

from sqlalchemy import select

from app.core import settings
from app.database.crud.mixines import GetBackNextIdMixin
from app.database import BackupDb


class BackupDbRepository(GetBackNextIdMixin[BackupDb]):
    model = BackupDb

    async def synchronize(self) -> None:
        db_items = await self.session.execute(select(self.model))
        items = [item.name for item in db_items.scalars().all()]

        path_dir = Path(settings.db.backups_dir)
        if path_dir.exists():
            files = [
                file.name
                for file in path_dir.iterdir()
                if file.is_file() and file.suffix == ".dump"
            ]
            for file in files:
                if file not in items:
                    self.session.add(self.model(name=file))
            for item in items:
                if item not in files:
                    obj_to_delete = await self.session.execute(
                        select(self.model).where(self.model.name == item)
                    )

                    if obj_to_delete:
                        await self.session.delete(obj_to_delete.scalar())
        await self.session.commit()
