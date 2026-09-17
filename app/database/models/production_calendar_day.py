"""
Модель локального кэша производственного календаря РФ.

Кэш нужен, чтобы:
1. Не зависеть от доступности внешнего сервиса isdayoff.ru на каждый
   запрос статистики.
2. Гарантировать стабильность уже посчитанных начислений: если внешний
   календарь у поставщика вдруг изменится (например, из-за переноса
   рабочих дней постановлением правительства уже после того, как по
   этому периоду были посчитаны выплаты), уже сохранённые в БД данные
   не изменятся молча задним числом при повторном запросе.
"""

from datetime import date as date_type

from sqlalchemy import Boolean, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseWithId


class ProductionCalendarDay(BaseWithId):
    """
    Один календарный день и его статус по производственному календарю РФ.

    is_working = True для рабочих и сокращённых рабочих дней (коды 0, 2, 4
    в терминах isdayoff.ru), False - для выходных и праздников (код 1).
    """

    __tablename__ = "production_calendar_days"
    __table_args__ = (UniqueConstraint("day", name="uq_production_calendar_days_day"),)

    day: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    is_working: Mapped[bool] = mapped_column(Boolean, nullable=False)
