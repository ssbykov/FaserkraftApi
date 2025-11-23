import io

import qrcode
from sqladmin import action
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.custom_model_view import CustomModelView
from app.admin.utils import check_superuser
from app.core import config
from app.core.auth.access_tokens_helper import AccessTokensHelper
from app.core.auth.user_manager_helper import UserManagerHelper
from app.database.crud.users import UsersRepository
from app.database.models import User
from app.tasks import run_process_mail


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

    @action(
        name="generate_qr",
        label="QR-код",
        add_in_detail=True,
        add_in_list=False,
        confirmation_message=f"Cоздать QR-код для пользователя?",
    )
    async def generate_qr(self, request: Request) -> RedirectResponse:
        pks = int(request.query_params["pks"])
        user_manager_helper = UserManagerHelper()
        user = await user_manager_helper.get_user_by_id(user_id=pks)
        access_tokens_helper = AccessTokensHelper()
        token = await access_tokens_helper.write_token(user=user)

        url = (
            f"http://{config.settings.run.host}"
            f":{config.settings.run.port}"
            f"/users/me"
        )
        qr_json = {"url": url, "token": token}

        img = qrcode.make(qr_json)
        byte_io = io.BytesIO()
        img.save(byte_io, format="PNG")
        byte_io.seek(0)
        context = {
            "name": user.email,
            "user_email": user.email,
            "qr_code_bytes": byte_io.getvalue(),
        }
        run_process_mail.delay(None, context=context, action="send_qr")
        return RedirectResponse(request.url_for("admin:list", identity=self.identity))
