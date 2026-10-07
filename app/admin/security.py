import os
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import PlainTextResponse


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


ADMIN_COOKIE_SECURE = env_bool("ADMIN_COOKIE_SECURE", True)

ADMIN_SESSION_MAX_AGE = int(
    os.getenv("ADMIN_SESSION_MAX_AGE", "3600")
)

ADMIN_IDLE_TIMEOUT = int(
    os.getenv("ADMIN_IDLE_TIMEOUT", "900")
)

ADMIN_ALLOWED_ORIGINS = frozenset(
    origin.strip().rstrip("/")
    for origin in os.getenv("ADMIN_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
)

if not ADMIN_ALLOWED_ORIGINS:
    raise RuntimeError(
        "Задайте ADMIN_ALLOWED_ORIGINS: "
        "список доверенных адресов админки без завершающего /"
    )

if ADMIN_SESSION_MAX_AGE <= 0 or ADMIN_IDLE_TIMEOUT <= 0:
    raise RuntimeError("Сроки административной сессии должны быть положительными")


def normalized_origin(value: str) -> str | None:
    try:
        parsed = urlsplit(value)

        if parsed.scheme not in {"http", "https"}:
            return None

        if not parsed.hostname or parsed.username or parsed.password:
            return None

        port = parsed.port
        default_port = 443 if parsed.scheme == "https" else 80

        host = parsed.hostname.lower()
        if ":" in host:
            host = f"[{host}]"

        suffix = f":{port}" if port and port != default_port else ""

        return f"{parsed.scheme}://{host}{suffix}"

    except ValueError:
        return None


TRUSTED_ORIGINS = frozenset(
    normalized_origin(value)
    for value in ADMIN_ALLOWED_ORIGINS
)

if None in TRUSTED_ORIGINS:
    raise RuntimeError("В ADMIN_ALLOWED_ORIGINS указан некорректный адрес")


class AdminRequestProtectionMiddleware:
    """
    Защита только административного sub-app.

    Для изменяющих запросов требуется доверенный Origin
    либо Referer. Изменяющие GET-actions запрещены.
    """

    SAFE_ACTIONS = frozenset({"back", "next"})

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        method = request.method.upper()

        # Защита от изменяющих запросов с другого сайта.
        if method not in {"GET", "HEAD", "OPTIONS"}:
            origin_header = request.headers.get("origin")

            if origin_header:
                origin = normalized_origin(origin_header)
            else:
                origin = normalized_origin(
                    request.headers.get("referer", "")
                )

            if origin not in TRUSTED_ORIGINS:
                response = PlainTextResponse(
                    "Источник административного запроса не разрешён.",
                    status_code=403,
                )
                await response(scope, receive, send)
                return

        # SQLAdmin custom actions в существующем проекте вызываются
        # ссылками. Разрешаем только навигационные действия.
        path_parts = [
            part for part in scope.get("path", "").split("/") if part
        ]

        if "action" in path_parts:
            action_index = path_parts.index("action")
            action_name = (
                path_parts[action_index + 1]
                if len(path_parts) > action_index + 1
                else ""
            )

            if action_name not in self.SAFE_ACTIONS:
                response = PlainTextResponse(
                    "Это действие временно отключено. "
                    "Требуется отдельный защищённый POST-обработчик.",
                    status_code=403,
                )
                await response(scope, receive, send)
                return

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}

                defaults = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"same-origin",
                    b"cache-control": b"no-store",
                    b"content-security-policy": (
                        b"frame-ancestors 'none'; "
                        b"base-uri 'self'; "
                        b"form-action 'self'"
                    ),
                }

                for name, value in defaults.items():
                    if name not in existing:
                        headers.append((name, value))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_security_headers)