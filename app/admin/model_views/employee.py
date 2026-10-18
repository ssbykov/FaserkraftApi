from sqladmin import action
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.custom_model_view import CustomModelView
from app.database import Employee
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

    action_in_header = ["send-qr"]

    @action(
        name="send-qr",
        label="Отправить QR-код",
        add_in_detail=True,
        add_in_list=False,
    )
    async def send_qr(self, request: Request) -> RedirectResponse:
        pk = int(request.query_params["pks"])
        return RedirectResponse(
            str(request.url_for("admin:employee_send_qr_form", pk=pk)),
            status_code=303,
        )