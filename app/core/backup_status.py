import json
import logging
from datetime import datetime
from typing import TypedDict

from app.core.redis import redis_client


logger = logging.getLogger(__name__)


class BackupStatus(TypedDict):
    running: bool
    ok: bool
    message: str
    finished_at: str


def save_last_result(name: str, ok: bool, message: str) -> None:
    """Сохранить результат последнего завершённого бэкапа."""
    payload = {
        "ok": ok,
        "message": message,
        "finished_at": datetime.now().astimezone().strftime(
            "%d.%m.%Y %H:%M:%S"
        ),
    }

    redis_client.set(
        f"{name}.last",
        json.dumps(payload, ensure_ascii=False),
    )


def get_backup_status(name: str) -> BackupStatus | None:
    """Вернуть состояние для баннера в админке."""
    try:
        if redis_client.exists(name):
            return {
                "running": True,
                "ok": False,
                "message": "Бэкап поставлен в очередь или выполняется.",
                "finished_at": "",
            }

        raw = redis_client.get(f"{name}.last")
        if raw is None:
            return None

        data = json.loads(raw)

        if not isinstance(data, dict):
            raise ValueError("Результат бэкапа должен быть JSON-объектом")

        if not isinstance(data.get("ok"), bool):
            raise ValueError("В результате бэкапа отсутствует поле ok")

        return {
            "running": False,
            "ok": data["ok"],
            "message": str(data.get("message", "")),
            "finished_at": str(data.get("finished_at", "")),
        }

    except Exception:
        logger.exception("Не удалось прочитать статус бэкапа из Redis")

        return {
            "running": False,
            "ok": False,
            "message": (
                "Не удалось получить статус бэкапа. "
                "Подробности в логах приложения."
            ),
            "finished_at": "",
        }