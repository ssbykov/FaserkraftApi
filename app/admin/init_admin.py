import os
from typing import Any, cast, Sequence, Awaitable, Iterable

from sqladmin import Admin
from sqladmin._types import ENGINE_TYPE
from sqladmin.authentication import login_required, AuthenticationBackend
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import sessionmaker
from starlette.applications import Starlette
from starlette.datastructures import URL
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse, JSONResponse

from app.core import settings
from app.database import db_helper, Process, StepDefinition, DailyPlan
from .backend import AdminAuth
from .custom_model_view import CustomModelView
from .model_views import (
    BackupDbAdmin,
    UserAdmin,
    ProcessAdmin,
    StepDefinitionAdmin,
    StepTemplateAdmin,
    ProductAdmin,
    ProductStepAdmin,
    EmployeeAdmin,
    DeviceAdmin,
    DailyPlanAdmin,
    DailyPlanStepAdmin,
)
from app.database.crud.employees import get_employee_repo


async def init_admin(app: Any) -> "NewAdmin":
    admin = NewAdmin(
        app,
        db_helper.engine,
        title="Производственный учет",
        templates_dir=str(settings.sql_admin.templates),
        authentication_backend=AdminAuth(secret_key=settings.sql_admin.secret),
    )
    admin.add_view(ProcessAdmin)
    admin.add_view(StepDefinitionAdmin)
    admin.add_view(StepTemplateAdmin)
    admin.add_view(ProductAdmin)
    admin.add_view(BackupDbAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(EmployeeAdmin)
    admin.add_view(ProductStepAdmin)
    admin.add_view(DeviceAdmin)
    admin.add_view(DailyPlanAdmin)
    admin.add_view(DailyPlanStepAdmin)
    assert isinstance(admin.authentication_backend, AdminAuth)
    await admin.authentication_backend.create_superuser()

    return admin


class NewAdmin(Admin):
    def __init__(
        self,
        app: Starlette,
        engine: ENGINE_TYPE | None = None,
        session_maker: sessionmaker | async_sessionmaker | None = None,  # type: ignore
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
        from starlette.exceptions import HTTPException as StarletteHTTPException

        async def http_exception(
            request: Request, exc: Exception
        ) -> Response | Awaitable[Response]:
            assert isinstance(exc, (StarletteHTTPException, HTTPException))
            status_code = getattr(exc, "status_code", 500)
            detail = getattr(exc, "detail", "Internal Server Error")

            # Если AJAX-запрос — возвращаем JSON, иначе шаблон
            is_ajax = (
                request.headers.get("x-requested-with") == "XMLHttpRequest"
                or request.headers.get("accept") == "application/json"
                or request.method == "DELETE"
            )

            if is_ajax:
                # Для AJAX — возвращаем JSON со специальным полем для редиректа
                return JSONResponse(
                    status_code=status_code,
                    content={"detail": detail},
                )

            # Для других ошибок — тоже используем шаблон
            context = {
                "status_code": status_code,
                "message": detail,
            }
            return await self.templates.TemplateResponse(
                request, "sqladmin/error.html", context, status_code=status_code
            )

        self.admin.exception_handlers = {HTTPException: http_exception}

    async def login(self, request: Request) -> Response:
        assert isinstance(self.authentication_backend, AdminAuth)

        context: dict[str, str | None] = {}
        if request.method == "GET":
            return await self.templates.TemplateResponse(request, "sqladmin/login.html")

        response = await self.authentication_backend.login_with_info(request)
        if not response.is_ok:
            context["error"] = response.error
            context["message"] = response.message
            return await self.templates.TemplateResponse(
                request, "sqladmin/login.html", context, status_code=400
            )
        await db_helper.synch_backups()
        return RedirectResponse(request.url_for("admin:index"), status_code=302)

    @login_required
    async def details(self, request: Request) -> Response:
        result = await super().details(request)
        if isinstance(result, RedirectResponse):
            return result
        context = result.context
        context["request"] = request
        return await self.templates.TemplateResponse(request, result.template, context)

    @staticmethod
    async def _fill_daily_plan_choices(form):
        async for session in db_helper.get_session():
            # 1. Сотрудники
            employee_repo = get_employee_repo(session)
            employees = await employee_repo.get_all()
            if hasattr(form, "employee_id"):
                form.employee_id.choices = [(e.id, str(e)) for e in employees]

            # 2. Процессы
            processes = (
                (await session.execute(select(Process).order_by(Process.name)))
                .scalars()
                .all()
            )
            process_choices = [(p.id, p.name) for p in processes]

            # 3. Этапы
            steps = (
                (
                    await session.execute(
                        select(StepDefinition)
                        .join(StepDefinition.work_process)
                        .order_by(Process.name, StepDefinition.order)
                    )
                )
                .scalars()
                .all()
            )
            step_choices = [(s.id, f"{s.work_process.name} — {s}") for s in steps]

            # 3.1. Плоская форма
            if hasattr(form, "process_id"):
                form.process_id.choices = process_choices
            if hasattr(form, "step_definition_id"):
                form.step_definition_id.choices = step_choices

            # 3.2. FieldList steps
            if hasattr(form, "steps") and isinstance(form.steps, Iterable):
                for subform in form.steps:
                    if hasattr(subform, "form"):
                        if hasattr(subform.form, "process_id"):
                            subform.form.process_id.choices = process_choices
                        if hasattr(subform.form, "step_definition_id"):
                            subform.form.step_definition_id.choices = step_choices

            # 4. Данные для JS
            processes_json = [{"id": p.id, "label": p.name} for p in processes]
            steps_by_process: dict[int, list[dict]] = {}
            for s in steps:
                pid = s.process_id
                steps_by_process.setdefault(pid, []).append(
                    {"id": s.id, "label": f"{s.order}: {s.template}"}
                )

            form.process_steps_map = {
                "processes": processes_json,
                "steps_by_process": steps_by_process,
            }

            break

    @staticmethod
    def _fill_daily_plan_steps(form, model: DailyPlan) -> None:
        """Синхронизировать form.steps с model.steps."""
        form.steps.min_entries = len(model.steps)
        while len(form.steps) < len(model.steps):
            form.steps.append_entry()

        for i, step in enumerate(model.steps):
            subform = form.steps[i].form  # DailyPlanStepForm

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
        """Edit model endpoint."""

        await self._edit(request)
        identity = request.path_params["identity"]
        model_view = self.find_custom_model_view(identity)

        model = await model_view.get_object_for_edit(request)
        if not model:
            raise HTTPException(status_code=404)

        Form = await model_view.scaffold_form(model_view._form_edit_rules)

        # --- GET ---
        if request.method == "GET":
            form = Form(obj=model, data=self._normalize_wtform_data(model))

            if isinstance(model, DailyPlan):
                await self._fill_daily_plan_choices(form)
                self._fill_daily_plan_steps(form, model)

            context = {
                "obj": model,
                "model_view": model_view,
                "form": form,
            }
            return await self.templates.TemplateResponse(
                request, model_view.edit_template, context
            )

        # --- POST ---
        form_data = await self._handle_form_data(request, model)
        form = Form(form_data, obj=model)  # WTForms-стиль [web:16][web:18]

        if isinstance(model, DailyPlan):
            await self._fill_daily_plan_choices(form)
            # WTForms сам создаст нужное количество entries из formdata [web:12][web:24]

        form_data_dict = self._denormalize_wtform_data(form.data, model)

        context = {
            "obj": model,
            "model_view": model_view,
            "form": form,
        }

        if not form.validate():
            context["error"] = "Пожалуйста, исправьте ошибки в форме."
            context["errors"] = form.errors
            return await self.templates.TemplateResponse(
                request, model_view.edit_template, context, status_code=400
            )

        try:
            restriction = await model_view.check_restrictions_create(
                form_data_dict, request
            )

            if restriction:
                context["error"] = restriction
                return await self.templates.TemplateResponse(
                    request, model_view.edit_template, context, status_code=400
                )

            pk = request.path_params["pk"]
            obj = await model_view.update_model(request, pk=pk, data=form_data_dict)

            url = self.get_save_redirect_url(
                request=request,
                form=form_data,
                obj=obj,
                model_view=model_view,
            )
            response = RedirectResponse(url=url, status_code=302)

            if hasattr(model_view, "get_page_for_url"):
                if page_suffix := await model_view.get_page_for_url(request):
                    response.headers["location"] += page_suffix
            return response

        except Exception as e:
            context["error"] = str(e)
            return await self.templates.TemplateResponse(
                request, model_view.edit_template, context, status_code=400
            )

    def find_custom_model_view(self, identity: str) -> CustomModelView[Any]:
        return cast(CustomModelView[Any], self._find_model_view(identity))

    async def delete(self, request: Request) -> Response:
        identity = request.path_params["identity"]
        model_view = self.find_custom_model_view(identity)

        restriction = await model_view.check_restrictions_delete(request)

        if restriction:
            raise HTTPException(detail=restriction, status_code=409)

        if isinstance(model_view, BackupDbAdmin):
            backup_id = int(request.query_params["pks"])
            if backup_db := await model_view.get_by_id(backup_id):
                file_path = os.path.join(settings.db.backups_dir, backup_db.name)
                if os.path.exists(file_path):
                    os.remove(file_path)
        try:
            result = await super().delete(request)
            return cast(Response, result)
        except Exception as e:
            if isinstance(e, IntegrityError):
                restriction = "Данная запись не может быть удалена из на нарушения целостности базы."
            else:
                restriction = str(e)
            return Response(
                status_code=409,
                content=restriction,
            )

    @login_required
    async def create(self, request: Request) -> Response:
        await self._create(request)

        identity = request.path_params["identity"]
        model_view = self.find_custom_model_view(identity)
        context: dict[str, Any] = {
            "model_view": model_view,
        }

        if isinstance(model_view, BackupDbAdmin):
            request.session["flash_messages"] = await model_view.create_backup()
            url = request.url_for("admin:list", identity=identity)
            return RedirectResponse(url=url, status_code=302)

        Form = await model_view.scaffold_form(model_view._form_create_rules)
        form_data = await self._handle_form_data(request)
        form = Form(form_data)

        context["form"] = form

        if request.method == "GET":
            return await self.templates.TemplateResponse(
                request, model_view.create_template, context
            )

        if not form.validate():
            context["error"] = "Пожалуйста, исправьте ошибки в форме."
            context["errors"] = form.errors
        else:
            form_data_dict = self._denormalize_wtform_data(form.data, model_view.model)
            try:

                restriction = await model_view.check_restrictions_create(form_data_dict)
                if restriction:
                    raise ValueError(restriction)

                obj = await model_view.insert_model(request, form_data_dict)
                url = cast(
                    URL,
                    self.get_save_redirect_url(
                        request=request,
                        form=form_data,
                        obj=obj,
                        model_view=model_view,
                    ),
                )
                return RedirectResponse(url=url, status_code=302)

            except Exception as e:
                context["error"] = str(e)
                if "days" in form_data_dict:
                    form_data_dict["days"] = []
                form.process(**form_data_dict)

        return await self.templates.TemplateResponse(
            request, model_view.create_template, context, status_code=400
        )

    @login_required
    async def list(self, request: Request) -> Any:
        response = await super().list(request)
        return response
