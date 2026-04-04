from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from celery import chain  # type: ignore

from app.tasks.create_backup import run_process_backup, backup_task

scheduler = AsyncIOScheduler()


async def backup_db() -> None:
    run_process_backup.delay()


async def startup_scheduler() -> None:
    # Настраиваем задачу на выполнение каждый день в заданное время
    scheduler.add_job(
        backup_db,
        CronTrigger(
            hour=1,
            minute=0,
            timezone="Europe/Moscow"
        ),
        misfire_grace_time=60,  # Допустимое время задержки (секунды)
    )

    # Запускаем планировщик
    scheduler.start()


async def shutdown_scheduler() -> None:
    scheduler.shutdown()
