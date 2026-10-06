from dataclasses import dataclass
from typing import Callable, Any

from celery import Celery  # type: ignore
from celery.result import AsyncResult  # type: ignore

from app.core.redis import REDIS_PATH, redis_client

LOCK_TTL = 6 * 3600
PENDING_VALUE = "pending"

celery_app = Celery("fkapi", broker=REDIS_PATH, backend=REDIS_PATH)
celery_app.conf.result_expires = 3600
celery_app.autodiscover_tasks(["app.tasks"])


@dataclass
class CeleryTask:
    name: str
    func: Callable[..., Any]


def try_acquire(name: str) -> bool:
    """Атомарно занять ключ. False — задача уже выполняется."""
    return bool(redis_client.set(name, PENDING_VALUE, nx=True, ex=LOCK_TTL))


def attach_task_id(name: str, task_id: str) -> None:
    """Записать id задачи, только если ключ ещё существует (xx)."""
    redis_client.set(name, task_id, ex=LOCK_TTL, xx=True)


def release(name: str) -> None:
    redis_client.delete(name)


def check_job_status(name: str) -> AsyncResult | None:
    """Вернуть активную задачу или None. Протухшие ключи чистятся."""
    value = redis_client.get(name)
    if not value:
        return None
    task_id = value.decode() if isinstance(value, bytes) else value
    if task_id == PENDING_VALUE:
        return None  # задача ставится в очередь прямо сейчас
    task = AsyncResult(task_id)
    if task.status in ("SUCCESS", "FAILURE"):
        release(name)
        return None
    return task
