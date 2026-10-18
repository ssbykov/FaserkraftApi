import logging
from pathlib import Path
from typing import Any, Awaitable, Iterable, Sequence, cast
from urllib.parse import quote

from sqladmin import Admin
from sqladmin._types import ENGINE_TYPE
from sqladmin.authentication import AuthenticationBackend, login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.admin.security import csrf_token
from app.admin.utils import check_superuser
from app.core import settings
from app.core.backup_status import get_backup_status
from app.database import DailyPlan, Process, StepDefinition, db_helper
from app.database.crud.employees import get_employee_repo
from app.services.device_invitations import (
    DeviceInvitationError,
    issue_device_invitation,
)
from app.tasks import run_process_mail
from app.utils.qr_code_gentrator import generate_qr_code
from .backend import AdminAuth
from .custom_model_view import CustomModelView
from .model_views import (
    BackupDbAdmin,
    DailyPlanAdmin,
    DailyPlanStepAdmin,
    DeviceAdmin,
    EmployeeAdmin,
    EmployeeNormCalculationAdmin,
    InventoryAdmin,
    InventoryItemAdmin,
    OrderAdmin,
    PackagingAdmin,
    ProcessAdmin,
    ProductAdmin,
    ProductStepAdmin,
    StepDefinitionAdmin,
    StepTemplateAdmin,
    UserAdmin,
)
from .model_views.size_type import SizeTypeAdmin

logger = logging.getLogger(__name__)


async def init_admin(app: Any) -> "NewAdmin":
    admin = NewAdmin(
        app,
        db_helper.engine,
        title="Производственный учет",
        templates_dir=str(settings.sql_admin.templates),
        authentication_backend=AdminAuth(
            secret_key=settings.sql_admin.secret,
        ),
    )

    # Функция для скрытых полей и метатега CSRF в шаблонах.
    admin.templates.env.globals["csrf_token"] = csrf_token

    def backup_status():
        return get_backup_status("tasks.backup")

    admin.templates.env.globals["backup_status"] = backup_status

    admin.add_view(ProcessAdmin)
    admin.add_view(SizeTypeAdmin)
    admin.add_view(StepDefinitionAdmin)
    admin.add_view(EmployeeNormCalculationAdmin)
    admin.add_view(StepTemplateAdmin)
    admin.add_view(ProductAdmin)
    admin.add_view(PackagingAdmin)
    admin.add_view(OrderAdmin)
    admin.add_view(InventoryAdmin)
    admin.add_view(InventoryItemAdmin)
    admin.add_view(BackupDbAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(EmployeeAdmin)
    admin.add_view(ProductStepAdmin)
    admin.add_view(DeviceAdmin)
    admin.add_view(DailyPlanAdmin)
    admin.add_view(DailyPlanStepAdmin)

    return admin


class NewAdmin(Admin):
    INVITATION_ERROR_TEXT = {
        "INVITATION_FORBIDDEN": "Недостаточно прав для выдачи приглашения.",
        "EMPLOYEE_NOT_FOUND": "Сотрудник не найден.",
        "EMPLOYEE_HAS_NO_USER": "У сотрудника нет привязанного пользователя.",
        "RECIPIENT_NOT_ALLOWED": (
            "Пользователь сотрудника должен быть активен и верифицирован."
        ),
    }

    def __init__(
        self,
        app: Starlette,
        engine: ENGINE_TYPE | None = None,
        session_maker: sessionmaker | async_sessionmaker | None = None,
        base_url: str = "/admin",
        title: str = "Admin",
        logo_url: str | None = None,
        favicon_url: str | None = None,
        middlewares: Sequence[Middleware] | None = None,
        debug: bool = False,
        templates_dir: str = "templates",
        authentication_backend: AuthenticationBackend | None = None,
    ) -> None:
        super().__init__(
            app=app,
            engine=engine,
            session_maker=session_maker,
            base_url=base_url,
            title=title,
            logo_url=logo_url,
            favicon_url=favicon_url,
            templates_dir=templates_dir,
            middlewares=middlewares,
            authentication_backend=authentication_backend,
        )

        # Отправка QR-кода сотруднику: страница подтверждения (GET)
        # и защищённая отправка (POST с CSRF-токеном).
        self.admin.add_route(
            "/employee/send-qr/{pk:int}",
            self.employee_send_qr_form,
            methods=["GET"],
            name="employee_send_qr_form",
        )
        self.admin.add_route(
            "/employee/send-qr/{pk:int}",
            self.employee_send_qr,
            methods=["POST"],
            name="employee_send_qr",
        )

        async def http_exception(
            request: Request,
            exc: Exception,
        ) -> Response | Awaitable[Response]:
            assert isinstance(exc, HTTPException)

            status_code = exc.status_code
            detail = exc.detail

            is_ajax = (
                request.headers.get("x-requested-with") == "XMLHttpRequest"
                or "application/json" in request.headers.get("accept", "")
                or request.method == "DELETE"
            )

            if is_ajax:
                return JSONResponse(
                    status_code=status_code,
                    content={"detail": detail},
                    headers=exc.headers,
                )

            return await self.templates.TemplateResponse(
                request,
                "sqladmin/error.html",
                {
                    "status_code": status_code,
                    "message": detail,
                },
                status_code=status_code,
                headers=exc.headers,
            )

        self.admin.exception_handlers[HTTPException] = http_exception

    async def login(self, request: Request) -> Response:
        assert isinstance(self.authentication_backend, AdminAuth)

        if request.method == "GET":
            return await self.templates.TemplateResponse(
                request,
                "sqladmin/login.html",
            )

        if request.method != "POST":
            raise HTTPException(status_code=405)

        result = await self.authentication_backend.login_with_info(
            request,
        )

        if not result.is_ok:
            status_code = getattr(
                request.state,
                "admin_login_status",
                400,
            )

            response = await self.templates.TemplateResponse(
                request,
                "sqladmin/login.html",
                {
                    "error": result.error,
                    "message": result.message,
                },
                status_code=status_code,
            )

            retry_after = getattr(
                request.state,
                "admin_login_retry_after",
                None,
            )

            if retry_after is not None:
                response.headers["Retry-After"] = str(retry_after)

            return response

        return RedirectResponse(
            request.url_for("admin:index"),
            status_code=303,
        )

    @login_required
    async def details(self, request: Request) -> Response:
        result = await super().details(request)

        if isinstance(result, RedirectResponse):
            return result

        context = result.context
        context["request"] = request

        return await self.templates.TemplateResponse(
            request,
            result.template,
            context,
        )

    # ------------------------------------------------------------------
    # Отправка QR-кода приглашения сотруднику
    # ------------------------------------------------------------------

    @staticmethod
    def _flash_error(url: str, message: str) -> RedirectResponse:
        return RedirectResponse(
            f"{url}?flash_error={quote(message)}",
            status_code=303,
        )

    @staticmethod
    async def _employee_qr_target(
        pk: int,
    ) -> tuple[str | None, str | None, str | None]:
        """Вернуть (имя сотрудника, email пользователя, текст ошибки)."""
        # Импорт внутри метода: иначе возникает циклический импорт
        # app.core.auth.user_manager_helper <-> app.api.
        from app.core.auth.user_manager_helper import UserManagerHelper

        async with db_helper.async_session() as session:
            employee = await get_employee_repo(session).get_by_id(pk)

            if employee is None:
                return None, None, "Сотрудник не найден."

            name, user_id = employee.name, employee.user_id

        if user_id is None:
            return name, None, "У сотрудника нет привязанного пользователя."

        user = await UserManagerHelper().get_user_by_id(user_id=user_id)

        if user is None or not user.is_active or not user.is_verified:
            return (
                name,
                None,
                "Нельзя отправить QR-код: пользователь должен быть "
                "активен и верифицирован.",
            )

        return name, user.email, None

    @login_required
    async def employee_send_qr_form(self, request: Request) -> Response:
        if not check_superuser(request):
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещён",
            )

        pk = int(request.path_params["pk"])
        details_url = str(request.url_for("admin:details", identity="employee", pk=pk))

        name, email, error = await self._employee_qr_target(pk)

        if error or email is None:
            return self._flash_error(details_url, error or "Ошибка.")

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/employee_send_qr.html",
            {
                "employee_id": pk,
                "employee_name": name,
                "email": email,
            },
        )

    @login_required
    async def employee_send_qr(self, request: Request) -> Response:
        if not check_superuser(request):
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещён",
            )

        pk = int(request.path_params["pk"])
        details_url = str(request.url_for("admin:details", identity="employee", pk=pk))

        admin_user = getattr(request.state, "admin_user", None)

        if admin_user is None:
            return self._flash_error(
                details_url,
                "Не удалось определить администратора.",
            )

        _, email, error = await self._employee_qr_target(pk)

        if error or email is None:
            return self._flash_error(details_url, error or "Ошибка.")

        try:
            result = await issue_device_invitation(
                actor_user_id=admin_user.id,
                employee_id=pk,
            )
        except DeviceInvitationError as exc:
            return self._flash_error(
                details_url,
                self.INVITATION_ERROR_TEXT.get(
                    exc.code,
                    "Не удалось создать приглашение.",
                ),
            )

        qr_code_bytes = generate_qr_code(
            {
                "employee_id": result.employee_id,
                "invitation_token": result.invitation_token,
            }
        )

        run_process_mail.delay(
            None,
            context={
                "name": email,
                "user_email": email,
                "qr_code_bytes": qr_code_bytes,
            },
            action="send_qr",
        )

        request.session["flash_messages"] = f"QR-код отправлен на {email}"

        return RedirectResponse(details_url, status_code=303)

    # ------------------------------------------------------------------
    # Ежедневные планы
    # ------------------------------------------------------------------

    @staticmethod
    async def _fill_daily_plan_choices(form: Any) -> None:
        async with db_helper.async_session() as session:
            employee_repo = get_employee_repo(session)
            employees = await employee_repo.get_all()

            if hasattr(form, "employee_id"):
                form.employee_id.choices = [
                    (employee.id, str(employee)) for employee in employees
                ]

            processes = (
                (await session.execute(select(Process).order_by(Process.name)))
                .scalars()
                .all()
            )

            process_choices = [(process.id, process.name) for process in processes]

            steps = (
                (
                    await session.execute(
                        select(StepDefinition)
                        .join(StepDefinition.work_process)
                        .order_by(
                            Process.name,
                            StepDefinition.order,
                        )
                    )
                )
                .scalars()
                .all()
            )

            step_choices = [
                (
                    step.id,
                    f"{step.work_process.name} — {step}",
                )
                for step in steps
            ]

            if hasattr(form, "process_id"):
                form.process_id.choices = process_choices

            if hasattr(form, "step_definition_id"):
                form.step_definition_id.choices = step_choices

            if hasattr(form, "steps") and isinstance(form.steps, Iterable):
                for subform in form.steps:
                    if not hasattr(subform, "form"):
                        continue

                    if hasattr(subform.form, "process_id"):
                        subform.form.process_id.choices = process_choices

                    if hasattr(
                        subform.form,
                        "step_definition_id",
                    ):
                        subform.form.step_definition_id.choices = step_choices

            processes_json = [
                {
                    "id": process.id,
                    "label": process.name,
                }
                for process in processes
            ]

            steps_by_process: dict[int, list[dict[str, Any]]] = {}

            for step in steps:
                steps_by_process.setdefault(
                    step.process_id,
                    [],
                ).append(
                    {
                        "id": step.id,
                        "label": f"{step.order}: {step.template}",
                    }
                )

            form.process_steps_map = {
                "processes": processes_json,
                "steps_by_process": steps_by_process,
            }

    @staticmethod
    def _fill_daily_plan_steps(
        form: Any,
        model: DailyPlan | None = None,
    ) -> None:
        """Заполнить шаги существующего плана или добавить пустой шаг."""
        if model and getattr(model, "steps", None):
            steps_count = len(model.steps)
        else:
            steps_count = 1

        form.steps.min_entries = steps_count

        while len(form.steps) < steps_count:
            form.steps.append_entry()

        if not model or not getattr(model, "steps", None):
            return

        for index, step in enumerate(model.steps):
            subform = form.steps[index].form

            if hasattr(subform, "process_id"):
                subform.process_id.data = step.step_definition.process_id

            if hasattr(subform, "step_definition_id"):
                subform.step_definition_id.data = step.step_definition_id

            if hasattr(subform, "planned_quantity"):
                subform.planned_quantity.data = step.planned_quantity

            if hasattr(subform, "actual_quantity"):
                subform.actual_quantity.data = step.actual_quantity

    @login_required
    async def edit(self, request: Request) -> Response:
        if not check_superuser(request):
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещён",
            )

        await self._edit(request)

        identity = request.path_params["identity"]
        model_view = self.find_custom_model_view(identity)

        model = await model_view.get_object_for_edit(request)

        if model is None:
            raise HTTPException(status_code=404)

        Form = await model_view.scaffold_form(
            model_view._form_edit_rules,
        )

        if request.method == "GET":
            form = Form(
                obj=model,
                data=self._normalize_wtform_data(model),
            )

            if isinstance(model, DailyPlan):
                await self._fill_daily_plan_choices(form)
                self._fill_daily_plan_steps(form, model)

            return await self.templates.TemplateResponse(
                request,
                model_view.edit_template,
                {
                    "obj": model,
                    "model_view": model_view,
                    "form": form,
                },
            )

        if request.method != "POST":
            raise HTTPException(status_code=405)

        form_data = await self._handle_form_data(
            request,
            model,
        )
        form = Form(form_data, obj=model)

        if isinstance(model, DailyPlan):
            await self._fill_daily_plan_choices(form)

        if not form.validate():
            return await self.templates.TemplateResponse(
                request,
                model_view.edit_template,
                {
                    "obj": model,
                    "model_view": model_view,
                    "form": form,
                    "error": "Пожалуйста, исправьте ошибки в форме.",
                    "errors": form.errors,
                },
                status_code=400,
            )

        data = self._denormalize_wtform_data(
            form.data,
            model,
        )
        pk = request.path_params["pk"]

        result: Any = await model_view.update_model(
            request,
            pk,
            data,
        )

        if isinstance(model, DailyPlan) and result.need_confirm:
            return await self.templates.TemplateResponse(
                request,
                model_view.edit_template,
                {
                    "obj": model,
                    "model_view": model_view,
                    "form": form,
                    "error": (
                        "План на эту дату для выбранного "
                        "сотрудника уже существует. "
                        "Сохранить изменения невозможно."
                    ),
                },
                status_code=400,
            )

        if isinstance(model, DailyPlan):
            result = result.obj

        return RedirectResponse(
            model_view._build_url_for(
                "admin:details",
                request,
                result,
            ),
            status_code=303,
        )

    def find_custom_model_view(
        self,
        identity: str,
    ) -> CustomModelView[Any]:
        return cast(
            CustomModelView[Any],
            self._find_model_view(identity),
        )

    @login_required
    async def delete(self, request: Request) -> Response:
        if not check_superuser(request):
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещён",
            )

        identity = request.path_params["identity"]
        model_view = self.find_custom_model_view(identity)

        if not model_view.is_accessible(request):
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещён",
            )

        if not model_view.can_delete:
            raise HTTPException(
                status_code=403,
                detail="Удаление запрещено",
            )

        restriction = await model_view.check_restrictions_delete(request)

        if restriction:
            raise HTTPException(
                status_code=409,
                detail=restriction,
            )

        backup_paths: list[Path] = []

        if isinstance(model_view, BackupDbAdmin):
            raw_pks = request.query_params.get("pks", "")

            try:
                backup_ids = [int(value) for value in raw_pks.split(",") if value]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Некорректные идентификаторы",
                )

            if not backup_ids or any(pk <= 0 for pk in backup_ids):
                raise HTTPException(
                    status_code=400,
                    detail="Некорректные идентификаторы",
                )

            root = Path(
                settings.db.backups_dir,
            ).resolve()

            for backup_id in backup_ids:
                backup = await model_view.get_by_id(
                    backup_id,
                )

                if backup is None:
                    continue

                path = (root / backup.name).resolve()

                if path.parent != root or path.suffix != ".dump":
                    logger.error(
                        "Отклонён путь резервной копии: " "backup_id=%s",
                        backup_id,
                    )

                    raise HTTPException(
                        status_code=400,
                        detail="Недопустимый путь резервной копии",
                    )

                backup_paths.append(path)

        try:
            result = await super().delete(request)

        except IntegrityError:
            logger.exception("Нарушение целостности при удалении в SQLAdmin")

            return Response(
                status_code=409,
                content="Удаление нарушает связи данных.",
            )

        except HTTPException:
            raise

        except Exception:
            logger.exception("Ошибка удаления в SQLAdmin")

            return Response(
                status_code=500,
                content="Не удалось удалить запись.",
            )

        if result.status_code < 400:
            for path in backup_paths:
                try:
                    path.unlink(missing_ok=True)

                except OSError:
                    logger.exception(
                        "Запись удалена, но файл бэкапа " "удалить не удалось"
                    )

        return cast(Response, result)

    @login_required
    async def create(self, request: Request) -> Response:
        if not check_superuser(request):
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещён",
            )

        await self._create(request)

        identity = request.path_params["identity"]
        model_view = self.find_custom_model_view(identity)

        if isinstance(model_view, BackupDbAdmin):
            if request.method == "GET":
                return await self.templates.TemplateResponse(
                    request,
                    "sqladmin/backup_create.html",
                    {
                        "model_view": model_view,
                    },
                )

            if request.method != "POST":
                raise HTTPException(status_code=405)

            message = await model_view.create_backup()

            if message:
                request.session["flash_messages"] = message

            return RedirectResponse(
                request.url_for(
                    "admin:list",
                    identity=identity,
                ),
                status_code=303,
            )

        Form = await model_view.scaffold_form(
            model_view._form_create_rules,
        )

        context: dict[str, Any] = {
            "model_view": model_view,
            "obj": None,
            "page_suffix": "",
        }

        if request.method == "GET":
            form = Form()

            if model_view.model is DailyPlan:
                await self._fill_daily_plan_choices(form)

            context["form"] = form

            return await self.templates.TemplateResponse(
                request,
                model_view.create_template,
                context,
            )

        if request.method != "POST":
            raise HTTPException(status_code=405)

        form_data = await self._handle_form_data(request)
        form = Form(form_data)

        if model_view.model is DailyPlan:
            await self._fill_daily_plan_choices(form)

        if not form.validate():
            context.update(
                form=form,
                error="Пожалуйста, исправьте ошибки в форме.",
                errors=form.errors,
            )

            return await self.templates.TemplateResponse(
                request,
                model_view.create_template,
                context,
                status_code=400,
            )

        data = self._denormalize_wtform_data(
            form.data,
            model_view.model,
        )

        result: Any = await model_view.insert_model(
            request,
            data,
        )

        if model_view.model is DailyPlan and result.need_confirm:
            context.update(
                form=form,
                error=(
                    "План на эту дату для выбранного "
                    "сотрудника уже существует. "
                    "Создание второго плана невозможно."
                ),
            )

            return await self.templates.TemplateResponse(
                request,
                model_view.create_template,
                context,
                status_code=400,
            )

        if model_view.model is DailyPlan:
            result = result.obj

        return RedirectResponse(
            model_view._build_url_for(
                "admin:details",
                request,
                result,
            ),
            status_code=303,
        )
