import logging
import re
from typing import Optional, TYPE_CHECKING, Union

from fastapi_users import (
    BaseUserManager,
    IntegerIDMixin,
    InvalidPasswordException,
)
from fastapi_users.schemas import UC

from app.core import settings, config
from app.database.models import User
from app.database.schemas.qr_data import QRData
from app.tasks import run_process_mail
from app.utils.qr_code_gentrator import generate_qr_code

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastapi import Request


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = settings.access_token.reset_password_token_secret
    verification_token_secret = settings.access_token.verification_token_secret

    async def on_after_register(
        self,
        user: User,
        request: Optional["Request"] = None,
    ) -> None:
        logger.warning("User %r has registered.", user.id)

    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Optional["Request"] = None,
    ) -> None:
        suffix_path = request.url.path.split("/")[-1]
        if suffix_path == "login":
            reset_url = (
                f"http://{config.settings.run.host}"
                f":{config.settings.run.port}"
                f"/{config.settings.api.auth_url}"
                f"/reset-password?token={token}"
            )
            context = {
                "user_email": user.email,
                "url_reset": reset_url,
            }
            run_process_mail.delay(None, context=context, action="forgot_password")
        elif suffix_path == "generate-qr":
            qr_data = QRData(
                action="register",
                id=user.id,
                token=token,
            )
            qr_code_bytes = generate_qr_code(qr_data)
            context = {
                "name": user.email,
                "user_email": user.email,
                "qr_code_bytes": qr_code_bytes,
            }
            run_process_mail.delay(None, context=context, action="send_qr")

        elif suffix_path == "get-qr-code":
            qr_json = {"action": "register", "id": user.id, "token": token}
            request.state.qr_data = qr_json

    async def on_after_request_verify(
        self,
        user: User,
        token: str,
        request: Optional["Request"] = None,
    ) -> None:
        verification_url = (
            f"http://{config.settings.run.host}"
            f":{config.settings.run.port}"
            f"/{config.settings.api.auth_url}"
            f"/verify?token={token}"
        )
        context = {
            "user_email": user.email,
            "token": token,
            "url_verification": verification_url,
        }
        run_process_mail.delay(None, context=context, action="verification")

    async def validate_password(
        self,
        password: str,
        user: Union[UC, User],
    ) -> None:

        if len(password) < 4:
            raise InvalidPasswordException(
                reason="Пароль должен быть не менее 8 символов"
            )
        if not re.search(r"\d", password):
            raise InvalidPasswordException(reason="Пароль должен содержать цифры")

        if not re.search(r"[A-Z]", password):
            raise InvalidPasswordException(
                reason="Пароль должен содержать заглавные буквы"
            )

        if not re.search(r"[a-z]", password):
            raise InvalidPasswordException(
                reason="Пароль должен содержать строчные буквы"
            )

        if user.email in password:
            raise InvalidPasswordException(reason="Пароль не должен содержать e-mail")
