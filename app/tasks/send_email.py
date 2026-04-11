from typing import Any

from app.celery_worker import celery_app, CeleryTask
from app.utils.email_sender import send_email
from app.tasks.get_or_create_loop import get_or_create_loop

mail_task = CeleryTask("tasks.mail", send_email)


@celery_app.task(name=mail_task.name)  # type: ignore
def run_process_mail(
    task_result: str, context: dict[str, Any], action: str | None = None
) -> Any:

    context["update_result"] = task_result

    loop = get_or_create_loop()
    return loop.run_until_complete(mail_task.func(context, action))
