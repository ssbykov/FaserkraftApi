from typing import Any, Callable, Type
from zoneinfo import ZoneInfo

from markupsafe import Markup
from sqlalchemy import Text
from sqlalchemy.orm import InstrumentedAttribute
from starlette.requests import Request

from app.database import BaseWithId


def check_superuser(request: Request) -> bool:
    user = getattr(request.state, "admin_user", None)

    return bool(
        user
        and user.is_active
        and user.is_verified
        and user.is_superuser
    )


def text_formater(
    model: Type[BaseWithId],
) -> dict[
    str | InstrumentedAttribute[Any],
    Callable[[Any, Any], Any],
]:
    def formatter(obj: Any, field: Any) -> Markup:
        value = getattr(obj, field, None)
        text = "" if value is None else str(value)

        return Markup(
            "<div style='white-space: pre-wrap; "
            "max-width: 800px;'>{}</div>"
        ).format(text)

    return {
        column.name: formatter
        for column in model.__table__.columns
        if isinstance(column.type, Text)
    }


def format_datetime(obj: Any, param: str) -> str:
    dt = getattr(obj, param, None)

    if dt is None:
        return ""

    return dt.astimezone(
        ZoneInfo("Europe/Moscow")
    ).strftime("%Y-%m-%d %H:%M:%S")