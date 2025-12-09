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
        confirmation_message=f"Cоздать QR-код для пользователя?",
    )
    async def generate_qr(self, request: Request) -> RedirectResponse:
        pks = int(request.query_params["pks"])
        async for session in db_helper.get_session():
            repo = self.repo_type(session)
            employee = await repo.get_by_id(obj_id=pks)

            user_manager_helper = UserManagerHelper()
            user = await user_manager_helper.get_user_by_id(user_id=employee.user_id)
            await user_manager_helper.forgot_password(user=user, request=request)

        return RedirectResponse(request.url_for("admin:list", identity=self.identity))
