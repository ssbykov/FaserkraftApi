import asyncio

from sqladmin import action
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.custom_model_view import CustomModelView
from app.admin.utils import check_superuser
from app.database import db_helper
from app.database.backup_db import restore_database_from_dump
from app.database.crud.backup_db import BackupDbRepository
from app.database.models.backup_db import BackupDb
from app.celery_worker import redis_client, check_job_status
from app.tasks.create_backup import run_process_backup, backup_task


class BackupDbAdmin(
    CustomModelView[BackupDb],
    model=BackupDb,
):
    repo_type = BackupDbRepository
    name_plural = "Резервные копии"
    name = "Резервная копия"
    icon = "fa-solid fa-box-archive"

    column_list = ("name",)
    column_labels = {
        "name": "Имя копии",
    }
    can_edit = False
    can_delete = True
    can_export = False
    can_view_details = False

    def is_visible(self, request: Request) -> bool:
        return check_superuser(request)

    def is_accessible(self, request: Request) -> bool:
        return check_superuser(request)

    async def get_by_id(self, backup_id: int) -> BackupDb | None:
        async for session in db_helper.get_session():
            repo = self.repo_type(session)
            return await repo.get_by_id(backup_id)
        return None

    @action(
        name="restore",
        label="Восстановить",
        add_in_detail=False,
        add_in_list=True,
        confirmation_message=f"Вы уверены, что хотите восстановить базу из резервной копии?"
        f"Будет использоавана последная отмеченная резервная копия.",
    )
    async def restore_db(self, request: Request) -> RedirectResponse:
        async for session in db_helper.get_session():
            if backup_id := request.query_params.get("pks", "").split(",")[-1]:
                repo = self.repo_type(session)
                if backup := await repo.get_by_id(int(backup_id)):
                    asyncio.create_task(restore_database_from_dump(backup.name))
                    return RedirectResponse(url="/admin/logout")
        return RedirectResponse(request.url_for("admin:list", identity=self.identity))

    @staticmethod
    async def create_backup() -> str | None:
        task = check_job_status(backup_task.name)

        # Если нет задачи или задача завершилась успешно — запускаем новый бэкап
        if not task or task.status == "SUCCESS":
            new_task = run_process_backup.delay()
            redis_client.set(run_process_backup.name, new_task.id)
            return None

        # Если задача завершилась неудачно — можно очистить ключ
        if task.status == "FAILURE":
            redis_client.delete(backup_task.name)
            # Вывести информацию об ошибке
            info = f"{type(getattr(task, 'result', None))}, {task.status}"
            return f"Ошибка: {info}"

        return "Предыдущий бэкап не закончен..."
