import logging
from datetime import datetime
from typing import Any

from celery import Task

from app.celery_worker import celery_app, CeleryTask
from app.core import settings
from app.database.backup_db import create_backup
from app.tasks.get_or_create_loop import get_or_create_loop


logger = logging.getLogger(__name__)

backup_task = CeleryTask("tasks.backup", create_backup)


class BackupTaskWithNotification(Task):
    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        try:
            from app.tasks.send_email import run_process_mail

            context = {
                "user_email": settings.email.admin_email,
                "task_id": task_id,
                "failed_at": datetime.now().astimezone().strftime(
                    "%d.%m.%Y %H:%M:%S"
                ),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

            run_process_mail.delay(
                "",
                context,
                "backup_failed",
            )

            logger.info(
                "Уведомление об ошибке бэкапа %s "
                "поставлено в очередь отправки",
                task_id,
            )

        except Exception:
            # Сбой уведомления не должен скрывать ошибку бэкапа.
            logger.exception(
                "Не удалось поставить в очередь письмо "
                "об ошибке бэкапа %s",
                task_id,
            )

        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    name=backup_task.name,
    base=BackupTaskWithNotification,
)
def run_process_backup() -> Any:
    loop = get_or_create_loop()
    return loop.run_until_complete(
        backup_task.func(backup_task.name)
    )