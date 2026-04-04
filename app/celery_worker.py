from dataclasses import dataclass
from typing import Callable, Any

from celery import Celery, Task  # type: ignore
from celery.result import AsyncResult  # type: ignore

from app.core.redis import REDIS_PATH, redis_client

celery_app = Celery("fkapi", broker=REDIS_PATH, backend=REDIS_PATH)

celery_app.conf.result_expires = 3600

celery_app.autodiscover_tasks(["app.tasks"])


def check_job_status(name: str) -> AsyncResult | None:
    task_id = redis_client.get(name)
    if not task_id:
        return None

    task = AsyncResult(task_id)
    # Если задача в конечном статусе — удаляем ключ
    if task.status in ("SUCCESS", "FAILURE"):
        redis_client.delete(name)
    return task if task.status not in ("SUCCESS", "FAILURE") else None


@dataclass
class CeleryTask:
    name: str
    func: Callable[..., Any]
