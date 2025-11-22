from dataclasses import dataclass
from typing import Callable, Any

import redis
from celery import Celery, Task  # type: ignore
from celery.result import AsyncResult  # type: ignore

from app.core import settings

HOST = settings.db.redis_host
PORT = 6379
DB = settings.db.redis_db

redis_client = redis.Redis(host=HOST, port=PORT, db=DB)

celery_app = Celery(
    "kkcalendar", broker=f"redis://{HOST}:{PORT}", backend=f"redis://{HOST}:{PORT}"
)

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
