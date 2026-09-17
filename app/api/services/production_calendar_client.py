"""
Клиент для получения данных производственного календаря РФ через
публичный API isdayoff.ru.

Документация: https://www.isdayoff.ru/desc/ и https://www.isdayoff.ru/extapi/
Формат запроса:
    https://isdayoff.ru/api/getdata?date1=YYYYMMDD&date2=YYYYMMDD&cc=ru&pre=1

Формат ответа: строка из цифр, один символ на каждый день диапазона:
    0 - рабочий день
    1 - нерабочий день (выходной/праздник)
    2 - сокращённый рабочий день (считаем как рабочий)
    4 - рабочий день по специальному постановлению (считаем как рабочий)
"""

from datetime import date as date_type
from datetime import timedelta

import httpx

ISDAYOFF_BASE_URL = "https://isdayoff.ru/api/getdata"

# Коды ответа, которые означают "рабочий день" для целей начисления зарплаты.
_WORKING_DAY_CODES = {"0", "2", "4"}


class ProductionCalendarError(Exception):
    """Не удалось получить данные производственного календаря."""


async def fetch_working_days_set(
    date_from: date_type,
    date_to: date_type,
    *,
    country_code: str = "ru",
    timeout_seconds: float = 5.0,
) -> set[date_type]:
    """
    Возвращает набор рабочих дат по производственному календарю РФ в
    диапазоне [date_from, date_to] включительно.

    Обращается к внешнему сервису isdayoff.ru. Поднимает
    ProductionCalendarError при сетевой ошибке, таймауте или неожидаемом
    формате ответа - вызывающий код (ProductionCalendarRepository)
    должен предусмотреть fallback на случай недоступности сервиса.
    """
    if date_from > date_to:
        raise ValueError("date_from не может быть позже date_to")

    params = {
        "date1": date_from.strftime("%Y%m%d"),
        "date2": date_to.strftime("%Y%m%d"),
        "cc": country_code,
        "pre": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(ISDAYOFF_BASE_URL, params=params)
            response.raise_for_status()
            raw_text = response.text.strip()
    except httpx.HTTPError as exc:
        raise ProductionCalendarError(
            f"Не удалось получить производственный календарь: {exc}"
        ) from exc

    expected_days = (date_to - date_from).days + 1
    if len(raw_text) != expected_days or not raw_text.isdigit():
        raise ProductionCalendarError(
            f"Некорректный формат ответа isdayoff.ru: {raw_text!r}"
        )

    working_days: set[date_type] = set()
    current_day = date_from
    for code in raw_text:
        if code in _WORKING_DAY_CODES:
            working_days.add(current_day)
        current_day += timedelta(days=1)

    return working_days
