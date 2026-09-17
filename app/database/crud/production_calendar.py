"""
Репозиторий для работы с локальным кэшем производственного календаря
и логика получения количества рабочих дней с fallback на внешний API.
"""

import logging
from datetime import date as date_type
from datetime import timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.services.production_calendar_client import (
    ProductionCalendarError,
    fetch_working_days_set,
)
from app.database import SessionDep


from app.database.models.production_calendar_day import ProductionCalendarDay

logger = logging.getLogger(__name__)


class ProductionCalendarRepository:
    def __init__(self, session: SessionDep) -> None:
        self.session = session

    async def get_cached_days(
        self,
        date_from: date_type,
        date_to: date_type,
    ) -> dict[date_type, bool]:
        """Возвращает {день: is_working} для дней, уже сохранённых в кэше."""
        stmt = select(
            ProductionCalendarDay.day,
            ProductionCalendarDay.is_working,
        ).where(
            ProductionCalendarDay.day >= date_from,
            ProductionCalendarDay.day <= date_to,
        )
        result = await self.session.execute(stmt)
        return {row.day: row.is_working for row in result.all()}

    async def save_days(self, days: dict[date_type, bool]) -> None:
        """Идемпотентно сохраняет статус дней в кэш (upsert по дате)."""
        if not days:
            return

        values = [
            {"day": day, "is_working": is_working}
            for day, is_working in days.items()
        ]

        stmt = pg_insert(ProductionCalendarDay).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[ProductionCalendarDay.day],
            set_={"is_working": stmt.excluded.is_working},
        )

        await self.session.execute(stmt)
        await self.session.commit()

    async def get_working_days_count(
        self,
        date_from: date_type,
        date_to: date_type,
    ) -> int:
        """
        Возвращает количество рабочих дней в диапазоне [date_from, date_to].

        Сначала проверяет локальный кэш. Для дней, которых в кэше нет,
        обращается к внешнему API isdayoff.ru и сохраняет результат в БД.
        Если внешний API недоступен, а часть дней не закэширована —
        оценивает недостающие дни по стандартной пятидневной неделе
        (пн-пт) как консервативный fallback, и логирует предупреждение.
        """
        cached = await self.get_cached_days(date_from, date_to)

        all_days = {
            date_from + timedelta(days=i)
            for i in range((date_to - date_from).days + 1)
        }
        missing_days = sorted(all_days - cached.keys())

        if missing_days:
            try:
                fetched_working_days = await fetch_working_days_set(
                    missing_days[0], missing_days[-1]
                )
                new_entries = {
                    day: day in fetched_working_days
                    for day in missing_days
                }
                await self.save_days(new_entries)
                cached.update(new_entries)
            except ProductionCalendarError:
                logger.warning(
                    "Не удалось получить производственный календарь "
                    "с isdayoff.ru для дней %s..%s. "
                    "Использую fallback по пн-пт без учёта праздников.",
                    missing_days[0],
                    missing_days[-1],
                )
                for day in missing_days:
                    cached[day] = day.weekday() < 5  # 0-4 = пн-пт

        return sum(1 for is_working in cached.values() if is_working)


def get_production_calendar_repo(
    session: SessionDep,
) -> ProductionCalendarRepository:
    return ProductionCalendarRepository(session)


ProductionCalendarRepoDep = Annotated[
    ProductionCalendarRepository, Depends(get_production_calendar_repo)
]
