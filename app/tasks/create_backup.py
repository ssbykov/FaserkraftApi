from typing import Any

from app.celery_worker import celery_app, CeleryTask
from app.database.backup_db import create_backup
from app.tasks.get_or_create_loop import get_or_create_loop

backup_task = CeleryTask("tasks.backup", create_backup)


@celery_app.task(name=backup_task.name)
def run_process_backup() -> Any:
    loop = get_or_create_loop()
    return loop.run_until_complete(backup_task.func(backup_task.name))
