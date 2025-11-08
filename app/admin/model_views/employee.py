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
    icon = "fa-solid fa-user"

    column_labels = {
        "name": "Имя",
        "role": "Роль",
    }

    column_list = (
        "name",
        "role",
    )

    column_details_list = (
        "name",
        "role",
        "telegram_id",
    )

    form_rules = [
        "name",
        "role",
        "telegram_id",
    ]

    can_export = False
