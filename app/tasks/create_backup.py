from typing import Any

from app.celery_worker import celery_app, CeleryTask
from app.database.backup_db import create_backup

backup_task = CeleryTask("tasks.backup", create_backup)


@celery_app.task(name=backup_task.name)
def run_process_backup() -> Any:
    import asyncio
    return asyncio.run(backup_task.func(backup_task.name))
