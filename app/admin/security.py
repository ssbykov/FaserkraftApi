import secrets
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.core import settings

ADMIN_COOKIE_SECURE = settings.admin_cookie_secure
ADMIN_SESSION_MAX_AGE = settings.admin_session_max_age
ADMIN_IDLE_TIMEOUT = settings.admin_idle_timeout
MAX_ADMIN_BODY = 8 * 1024 * 1024


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


_origins = [v.strip() for v in settings.admin_allowed_origins.split(",") if v.strip()]
TRUSTED_ORIGINS = frozenset(normalized_origin(v) for v in _origins)
if not TRUSTED_ORIGINS or None in TRUSTED_ORIGINS:
    raise RuntimeError("Задайте корректный ADMIN_ALLOWED_ORIGINS")


def csrf_token(request: Request) -> str:
    token = request.session.get("admin_csrf")
    if not isinstance(token, str) or len(token) != 64:
        token = secrets.token_hex(32)
        request.session["admin_csrf"] = token
    return token


class AdminRequestProtectionMiddleware:
    SAFE_ACTIONS = frozenset({"back", "next", "send-qr"})

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        downstream_receive = receive

        async def reject(message: str, status: int = 403):
            response = PlainTextResponse(
                message,
                status_code=status,
                headers={
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
            await response(scope, receive, send)

        parts = [p for p in scope.get("path", "").split("/") if p]
        if "action" in parts:
            index = parts.index("action")
            name = parts[index + 1] if len(parts) > index + 1 else ""
            if name not in self.SAFE_ACTIONS:
                await reject("Действие отключено до перевода на защищённый POST.")
                return

        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin_header = request.headers.get("origin")
            origin = normalized_origin(
                origin_header
                if origin_header is not None
                else request.headers.get("referer", "")
            )
            if origin not in TRUSTED_ORIGINS:
                await reject("Источник административного запроса не разрешён.")
                return

            expected = request.session.get("admin_csrf")
            if not isinstance(expected, str) or len(expected) != 64:
                await reject("CSRF-сессия отсутствует. Обновите страницу.")
                return

            chunks = []
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    continue
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > MAX_ADMIN_BODY:
                    await reject("Размер запроса превышает 8 МиБ.", 413)
                    return
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break

            body = b"".join(chunks)

            def replay_receiver():
                delivered = False

                async def replay():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {
                            "type": "http.request",
                            "body": body,
                            "more_body": False,
                        }
                    return await receive()

                return replay

            submitted = request.headers.get("x-csrf-token")
            if submitted is None:
                content_type = (
                    request.headers.get("content-type", "").split(";", 1)[0].lower()
                )
                if content_type not in {
                    "application/x-www-form-urlencoded",
                    "multipart/form-data",
                }:
                    await reject("Требуется заголовок X-CSRF-Token.")
                    return
                try:
                    parsed_request = Request(scope, replay_receiver())
                    async with parsed_request.form() as form:
                        values = form.getlist("csrf_token")
                        submitted = values[0] if len(values) == 1 else None
                except Exception:
                    await reject("Некорректная форма запроса.", 400)
                    return

            if (
                not isinstance(submitted, str)
                or len(submitted) != 64
                or not secrets.compare_digest(expected, submitted)
            ):
                await reject("Неверный CSRF-токен. Обновите страницу.")
                return

            downstream_receive = replay_receiver()

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
                        b"frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
                    ),
                }
                for name, value in defaults.items():
                    if name not in existing:
                        headers.append((name, value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, downstream_receive, send_with_security_headers)
