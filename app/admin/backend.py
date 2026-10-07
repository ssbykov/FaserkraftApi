import logging
import time

from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.exceptions import UserNotExists
from sqladmin.authentication import AuthenticationBackend
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from app.admin.security import (
    ADMIN_COOKIE_SECURE,
    ADMIN_IDLE_TIMEOUT,
    ADMIN_SESSION_MAX_AGE,
    AdminRequestProtectionMiddleware,
)
from app.core import settings
from app.core.auth.access_tokens_helper import AccessTokensHelper
from app.core.auth.user_manager_helper import UserManagerHelper
from app.database.schemas.admin_auth_response import AdminAuthResponse

logger = logging.getLogger(__name__)


class AdminAuth(AuthenticationBackend):
    def __init__(
        self,
        secret_key: str = settings.sql_admin.secret,
    ) -> None:
        if len(secret_key) < 32:
            raise ValueError(
                "Для админки требуется отдельный случайный "
                "secret_key длиной не менее 32 символов"
            )

        super().__init__(secret_key=secret_key)

        self.middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=secret_key,
                session_cookie="fk_admin_session",
                max_age=ADMIN_SESSION_MAX_AGE,
                same_site="strict",
                https_only=ADMIN_COOKIE_SECURE,
            ),
            Middleware(AdminRequestProtectionMiddleware),
        ]

        self.user_manager_helper = UserManagerHelper()
        self.access_tokens_helper = AccessTokensHelper()

    @staticmethod
    def _allowed(user) -> bool:
        return bool(user and user.is_active and user.is_verified and user.is_superuser)

    async def login(self, request: Request) -> bool:
        result = await self.login_with_info(request)
        return result.is_ok

    async def login_with_info(
        self,
        request: Request,
    ) -> AdminAuthResponse:
        if request.method != "POST":
            return AdminAuthResponse(
                is_ok=False,
                error="Недопустимый метод запроса.",
            )

        form = await request.form()

        action = form.get("action", "login")
        username = form.get("username")
        password = form.get("password")

        # Публичная регистрация и восстановление через форму админки
        # отключены. API-маршруты этим не изменяются.
        if action != "login":
            return AdminAuthResponse(
                is_ok=False,
                error="Действие недоступно.",
            )

        if (
            not isinstance(username, str)
            or not isinstance(password, str)
            or not username.strip()
            or not password
            or len(username) > 320
            or len(password) > 1024
        ):
            return AdminAuthResponse(
                is_ok=False,
                error="Неверный логин или пароль.",
            )

        credentials = OAuth2PasswordRequestForm(
            username=username.strip(),
            password=password,
        )

        try:
            user = await self.user_manager_helper.get_user(credentials=credentials)

            if not self._allowed(user):
                return AdminAuthResponse(
                    is_ok=False,
                    error="Неверный логин или пароль.",
                )

            # Отзываем предыдущую административную сессию
            # этого браузера, если она существует.
            await self.logout(request)

            token = await self.access_tokens_helper.write_token(user=user)
            if not token:
                raise RuntimeError("Не удалось создать токен админки")

            now = time.time()

            request.session.clear()
            request.session.update(
                {
                    "token": token,
                    "admin_login_at": now,
                    "admin_last_seen_at": now,
                }
            )

            request.state.admin_user = user

            logger.info(
                "Успешный вход в SQLAdmin: user_id=%s",
                user.id,
            )

            return AdminAuthResponse(is_ok=True)

        except Exception:
            logger.exception("Ошибка входа в SQLAdmin")

            return AdminAuthResponse(
                is_ok=False,
                error="Не удалось выполнить вход. Повторите позже.",
            )

    async def logout(self, request: Request) -> bool:
        token = request.session.get("token")

        request.session.clear()
        request.state.admin_user = None

        if isinstance(token, str) and token:
            try:
                access_token = await self.access_tokens_helper.get_access_token(
                    token=token
                )

                if access_token:
                    user = await self.user_manager_helper.get_user_by_id(
                        user_id=access_token.user_id
                    )

                    await self.access_tokens_helper.destroy_token(
                        token=token,
                        user=user,
                    )

            except UserNotExists:
                logger.warning("Пользователь административной сессии удалён")

            except Exception:
                logger.exception("Не удалось отозвать административный токен")

        return True

    async def authenticate(self, request: Request) -> bool:
        request.state.admin_user = None

        token = request.session.get("token")
        login_at = request.session.get("admin_login_at")
        last_seen_at = request.session.get("admin_last_seen_at")

        if not isinstance(token, str) or not token:
            return False

        if not isinstance(login_at, (int, float)) or not isinstance(
            last_seen_at, (int, float)
        ):
            await self.logout(request)
            return False

        now = time.time()

        if (
            now < login_at
            or now < last_seen_at
            or now - login_at >= ADMIN_SESSION_MAX_AGE
            or now - last_seen_at >= ADMIN_IDLE_TIMEOUT
        ):
            await self.logout(request)
            return False

        try:
            access_token = await self.access_tokens_helper.get_access_token(token=token)

            if not access_token:
                await self.logout(request)
                return False

            if not await self.access_tokens_helper.check_access_token(
                token=access_token
            ):
                await self.logout(request)
                return False

            user = await self.user_manager_helper.get_user_by_id(
                user_id=access_token.user_id
            )

            if not self._allowed(user):
                await self.logout(request)
                return False

            request.state.admin_user = user
            request.session["admin_last_seen_at"] = now

            return True

        except UserNotExists:
            await self.logout(request)
            return False

        except Exception:
            logger.exception("Ошибка проверки административной сессии")
            # Не разрешаем доступ при ошибке проверки.
            return False
