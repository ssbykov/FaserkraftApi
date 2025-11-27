from starlette.requests import Request

from app.admin.custom_model_view import CustomModelView
from app.admin.utils import check_superuser
from app.database.crud.users import UsersRepository
from app.database.models import User


class UserAdmin(
    CustomModelView[User],
    model=User,
):
    repo_type = UsersRepository
    name_plural = "Пользователи"
    name = "Пользователь"
    category = "Пользователи"
    category_icon = "fa-solid fa-user"

    column_labels = {
        "created_at": "Создан",
        "updated_at": "Изменен",
    }

    column_list = (
        "id",
        "email",
        "is_verified",
    )
    column_details_exclude_list = (
        "user",
        "hashed_password",
    )
    form_excluded_columns = (
        "user",
        "hashed_password",
        "created_at",
        "updated_at",
    )

    can_export = False
    can_create = False

    def is_visible(self, request: Request) -> bool:
        return check_superuser(request)

    def is_accessible(self, request: Request) -> bool:
        return check_superuser(request)
