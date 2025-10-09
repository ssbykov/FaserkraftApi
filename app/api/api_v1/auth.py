from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi_users.exceptions import InvalidVerifyToken, UserAlreadyVerified
from starlette.templating import _TemplateResponse

from app.api.dependencies.backend import authentication_backend
from app.core import config
from app.core.config import settings
from app.database.schemas.user import UserRead, UserCreate
from app.tasks import run_process_mail
from .fastapi_users import fastapi_users
from ..dependencies.user_manager import get_user_manager

templates = Jinja2Templates(directory=settings.sql_admin.templates)

router = APIRouter(
    prefix=settings.api.v1.auth,
    tags=["Auth"],
)

if TYPE_CHECKING:
    from app.core.auth.user_manager import UserManager


@router.get("/verify")
async def verify_user(
    token: str, user_manager: "UserManager" = Depends(get_user_manager)
) -> str:
    try:
        user = await user_manager.verify(token=token)
        url = (
            f"http://{config.settings.run.host}"
            f":{config.settings.run.port}"
            f"/admin/login"
        )
        context = {
            "user_email": user.email,
            "token": token,
            "url": url,
        }
        run_process_mail.delay(None, context=context, action="verify_confirmation")

        return f"Пользователь {user.email} верифицирован."
    except InvalidVerifyToken:
        return "Невалидный токен"
    except UserAlreadyVerified:
        return "Пользователь уже верифицирован"


@router.get("/reset-password")
def reset_password_form(request: Request) -> _TemplateResponse:
    token = request.query_params.get("token")
    return templates.TemplateResponse(
        "reset_password.html", {"request": request, "token": token}
    )


# login, logout
router.include_router(
    router=fastapi_users.get_auth_router(
        authentication_backend,
        requires_verification=True,
    ),
)

# register
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)

# verify
router.include_router(router=fastapi_users.get_verify_router(UserRead))

router.include_router(router=fastapi_users.get_reset_password_router())
