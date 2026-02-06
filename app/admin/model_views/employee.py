import base64
from urllib.parse import quote

from sqladmin import action
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.custom_model_view import CustomModelView
from app.core.auth.user_manager_helper import UserManagerHelper
from app.database import Employee, db_helper
from app.database.crud.employees import EmployeeRepository


class EmployeeAdmin(
    CustomModelView[Employee],
    model=Employee,
):
    repo_type = EmployeeRepository
    name_plural = "Сотрудники"
    name = "Сотрудник"
    category = "Пользователи"

    column_labels = {
        "name": "Имя",
        "role": "Роль",
        "user": "Пользователь",
        "device": "Устройство",
        "telegram_id": "Телеграмм",
    }

    column_list = (
        "name",
        "role",
    )

    column_details_list = (
        "name",
        "role",
        "user",
        "telegram_id",
        "device_id",
    )

    form_rules = [
        "name",
        "role",
        "user",
        "telegram_id",
        "device",
    ]

    can_export = False

    action_in_header = ["generate-qr"]

    @action(
        name="generate-qr",
        label="QR-код",
        add_in_detail=True,
        add_in_list=False,
        confirmation_message=f"Создать QR-код для пользователя?",
    )
    async def generate_qr(self, request: Request) -> RedirectResponse:
        pks = int(request.query_params["pks"])
        async for session in db_helper.get_session():
            repo = self.repo_type(session)
            employee = await repo.get_by_id(obj_id=pks)

            user_manager_helper = UserManagerHelper()
            user = await user_manager_helper.get_user_by_id(user_id=employee.user_id)

            if not user.is_active or not user.is_verified or user.is_superuser:
                error_msg = "Нельзя сгенерировать QR-код: пользователь должен быть активен, верифицирован и не быть суперпользователем."

                # Просто используем URL encoding
                encoded_error = quote(error_msg)

                detail_url = str(
                    request.url_for("admin:details", identity=self.identity, pk=pks)
                )
                return RedirectResponse(
                    f"{detail_url}?flash_error={encoded_error}",
                    status_code=303,
                )
            await user_manager_helper.forgot_password(user=user, request=request)

        return RedirectResponse(request.url_for("admin:list", identity=self.identity))
