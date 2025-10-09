from typing import Any

from app.celery_worker import celery_app, CeleryTask
from app.database.backup_db import create_backup

backup_task = CeleryTask("tasks.backup", create_backup)


@celery_app.task(name=backup_task.name)  # type: ignore
def run_process_backup(*args: Any) -> Any:
    import asyncio

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(backup_task.func(*args))
