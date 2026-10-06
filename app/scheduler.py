import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.celery_worker import (
    attach_task_id,
    release,
    try_acquire,
)
from app.tasks.create_backup import backup_task, run_process_backup


logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def backup_db() -> None:
    if not try_acquire(backup_task.name):
        logger.info(
            "Бэкап по расписанию пропущен: "
            "предыдущий бэкап ещё не завершён"
        )
        return

    try:
        result = run_process_backup.delay()
        attach_task_id(backup_task.name, result.id)

    except Exception:
        try:
            release(backup_task.name)
        except Exception:
            logger.exception(
                "Не удалось снять блокировку "
                "после ошибки запуска бэкапа по расписанию"
            )

        logger.exception(
            "Не удалось поставить бэкап по расписанию в очередь"
        )
        raise

    logger.info(
        "Бэкап по расписанию поставлен в очередь: %s",
        result.id,
    )


async def startup_scheduler() -> None:
    scheduler.add_job(
        backup_db,
        CronTrigger(
            hour=1,
            minute=0,
            timezone="Europe/Moscow",
        ),
        id="daily_database_backup",
        replace_existing=True,
        misfire_grace_time=60,
        max_instances=1,
    )

    if not scheduler.running:
        scheduler.start()


async def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()